import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from src.brain_core.action_engine.contracts import ActionRequest, ConversationalDirective
from src.brain_core.context_engine.ccc_contracts import (
    CustomerConversationContext, 
    CustomerContext, 
    OrderContext, 
    ProductContext, 
    CustomerConversationProjection
)
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessRealityStatus
from src.shared.rabta_interfaces import ContextExecutionAdapter
from types import SimpleNamespace


def _summarize_action_history(action_history: Optional[list]) -> Optional[str]:
    """
    Renders ShopDeck's action_history (calls, SMS, WhatsApp attempts and their responses -
    see NDRActionHistory in business_systems/shopdeck's ndr schema) into a short, flat
    summary line so Priya knows what outreach has already happened and how the customer
    responded, instead of starting the conversation with no memory of it. Kept short and
    factual - never invents a response that isn't in the data.
    """
    if not action_history:
        return "No prior outreach recorded for this order."
    lines = []
    for entry in action_history:
        action_type = entry.get("action_type", "unknown_action")
        response_status = entry.get("response_status")
        part = f"{action_type} -> {response_status}" if response_status else f"{action_type} -> no response recorded"
        message_text = entry.get("message_text")
        if message_text:
            part += f" (message: \"{message_text}\")"
        if entry.get("is_priority_escalate"):
            part += " [escalated]"
        lines.append(part)
    return "; ".join(lines)


class CustomerConversationContextBuilder:
    """
    Builds the immutable CustomerConversationContext snapshot by resolving identifiers 
    (like awb_no) against authorized Context Providers (like ShopdeckCemAdapter).
    """
    def __init__(self, provider: ContextExecutionAdapter, inventory_provider: Optional[ContextExecutionAdapter] = None):
        self.provider = provider
        self.inventory_provider = inventory_provider
        
    async def build(self, action_request: ActionRequest) -> CustomerConversationContext:
        awb_no = action_request.parameters.get("awb_no")
        if not awb_no:
            raise ValueError("Cannot build CCC without an awb_no identifier in ActionRequest parameters.")
            
        directive = action_request.directive
        if not directive:
            raise ValueError("Cannot build CCC without a ConversationalDirective in the ActionRequest.")

        from src.shared.requirement_classification_contracts import ClassifiedRequirement
        from src.shared.conversational_contracts import ConversationalUnderstanding, NormalizedParameter, ParameterDataType, SemanticEntityReference
        req = AbstractEvidenceRequest(
            classified_requirement=ClassifiedRequirement(
                understanding=ConversationalUnderstanding(
                    original_query=f"Internal CCC Hydration for AWB {awb_no}",
                    parameters=[NormalizedParameter(parameter_name="awb_no", data_type=ParameterDataType.STRING, value=awb_no, original_expression=awb_no)]
                )
            )
        )
        response = await self.provider.execute_evidence_request(req)
        
        if response.status != BusinessRealityStatus.EVIDENCE_AVAILABLE:
            raise RuntimeError(f"Failed to hydrate CCC. Provider returned status: {response.status}")
            
        evidence = response.evidence_data
        
        phone = evidence.get("customer.attribute.phone")
        
        # Bypassing DB corruption: If Shopdeck DB lookup failed, fallback to test override
        from src.shared.config import settings
        if not phone and getattr(settings, "test_phone_override", None):
            phone = settings.test_phone_override
            
        if not phone:
            raise ValueError("ShopDeck BS did not provide an authoritative customer phone number.")
            
        # 1. Hydrate Customer Context
        customer_ctx = CustomerContext(
            name=evidence.get("customer_name"),
            phone=phone
        )
        
        # 2. Hydrate Order Context
        order_ctx = OrderContext(
            awb_no=awb_no,
            collectable_amount=float(evidence.get("cod_amount") or 0.0),
            payment_mode=evidence.get("payment_mode", "UNKNOWN"),
            courier_partner=evidence.get("courier_partner"),
            past_delivery_attempts=evidence.get("ndr_count"),
            destination_pincode=evidence.get("drop_pincode"),
            prior_communication_summary=_summarize_action_history(evidence.get("action_history")),
        )
        
        # 3. Hydrate Product Context
        items = evidence.get("items", [])
        if items and len(items) > 0:
            first_item = items[0]
            sku_id = first_item.get("sku_id")
            
            # Extract actual order commercial truth from ShopDeck item
            actual_item_price = float(first_item.get("selling_price", 0.0))
            order_quantity = first_item.get("quantity")
            
            # Reconstruct OrderContext with item details
            order_ctx = OrderContext(
                awb_no=order_ctx.awb_no,
                collectable_amount=order_ctx.collectable_amount,
                payment_mode=order_ctx.payment_mode,
                actual_item_price=actual_item_price,
                order_quantity=order_quantity,
                courier_partner=order_ctx.courier_partner,
                past_delivery_attempts=order_ctx.past_delivery_attempts,
                destination_pincode=order_ctx.destination_pincode,
                prior_communication_summary=order_ctx.prior_communication_summary,
            )
            
            product_description = None
            rich_attributes_available = False
            
            # Fetch enriched description from Inventory BS
            product_name = first_item.get("product_name")
            if (sku_id or product_name) and self.inventory_provider:
                entities = []
                if sku_id:
                    entities.append(SemanticEntityReference(inferred_type="item_code", original_expression=sku_id))
                elif product_name:
                    entities.append(SemanticEntityReference(inferred_type="product_name", original_expression=product_name))
                
                query_desc = sku_id if sku_id else product_name
                inv_req = AbstractEvidenceRequest(
                    classified_requirement=ClassifiedRequirement(
                        understanding=ConversationalUnderstanding(
                            intent="SEARCH",
                            original_query=f"Get details for {query_desc}",
                            entities=entities
                        )
                    )
                )
                inv_response = await self.inventory_provider.execute_evidence_request(inv_req, "")
                if inv_response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE and inv_response.evidence_data:
                    inv_data = inv_response.evidence_data
                    product_description = inv_data.get("description")
                    
                    # Inventory BS is the authoritative catalog source for product naming
                    if inv_data.get("product_name"):
                        first_item["product_name"] = inv_data["product_name"]
                        
                    rich_attributes_available = True
            
            product_ctx = ProductContext(
                sku_id=sku_id,
                product_code=first_item.get("product_code"),
                product_name=first_item.get("product_name"),
                product_description=product_description,
                catalog_selling_price=float(inv_data.get("selling_price")) if (rich_attributes_available and inv_data.get("selling_price") is not None) else None,
                mrp=inv_data.get("mrp") if (rich_attributes_available and inv_data) else None,
                image_url=inv_data.get("image_url") if (rich_attributes_available and inv_data) else None,
                size=inv_data.get("size") if (rich_attributes_available and inv_data) else None,
                color=inv_data.get("color") if (rich_attributes_available and inv_data) else None,
                material=inv_data.get("material") if (rich_attributes_available and inv_data) else None,
                features=inv_data.get("features") if (rich_attributes_available and inv_data) else None,
                return_exchange_condition=inv_data.get("return_exchange_condition") if (rich_attributes_available and inv_data) else None,
                attr_style=inv_data.get("attr_style") if (rich_attributes_available and inv_data) else None,
                attr_pattern=inv_data.get("attr_pattern") if (rich_attributes_available and inv_data) else None,
                attr_package_contents=inv_data.get("attr_package_contents") if (rich_attributes_available and inv_data) else None,
                rich_attributes_available=rich_attributes_available
            )
        else:
            product_ctx = ProductContext(rich_attributes_available=False)
            
        return CustomerConversationContext(
            ccc_id=f"ccc_{uuid.uuid4().hex[:8]}",
            target_identity=awb_no,
            customer_profile=customer_ctx,
            order_facts=order_ctx,
            product_context=product_ctx,
            directive=directive
        )
        
    def project(self, ccc: CustomerConversationContext) -> CustomerConversationProjection:
        """
        Projects the full CCC into a governed, customer-safe subset for PRIYA LLM consumption.
        Strips away all internal IDs and focuses purely on conversational facts.
        Injects immutable Core Safety Policy independent of Domain directives.
        """
        CORE_SAFETY_POLICY = [
            "Never execute a financial transaction.",
            "Do not disclose internal system IDs or logic.",
            "Do not invent unauthoritative products, names, or reasons.",
            "Never claim an action has been completed (e.g. rescheduled, cancelled) without explicit execution confirmation from the authorized system."
        ]

        mission = ccc.directive.mission

        # Reschedule window is policy, not code - read from NDR-domain config, keyed by
        # attempt number, rather than hardcoding day counts here. A 0-day window (e.g. the
        # 3rd attempt) means no reattempt date is offered at all.
        from src.intelligence_domains.ndr.config import ndr_settings
        attempt_count = ccc.order_facts.past_delivery_attempts or 1
        window_days = ndr_settings.reschedule_window_days.get(str(attempt_count), 2)
        offered_date_1 = (datetime.now() + timedelta(days=1)).strftime("%A (%d-%m-%Y)") if window_days >= 1 else None
        offered_date_2 = (datetime.now() + timedelta(days=2)).strftime("%A (%d-%m-%Y)") if window_days >= 2 else None

        # By user decision: from the 2nd failed attempt onward, recording why prior
        # deliveries failed (in the customer's own words) becomes a primary objective, not
        # an optional aside. Never set on the 1st attempt (nothing prior to review), and
        # moot on the 3rd+ since no call is dispatched for those per the risk engine's
        # policy_allows_autonomous_action check.
        diagnostic_priority_instruction = None
        if (ccc.order_facts.past_delivery_attempts or 0) >= 2:
            diagnostic_priority_instruction = (
                "This is not the first delivery attempt. Before discussing anything else, "
                "ask the customer directly why the earlier delivery attempt(s) did not "
                "succeed, in their own words, and make sure that reason is clearly stated "
                "in the conversation - this is a primary objective of this call, not a "
                "secondary detail. prior_communication_summary shows what was already "
                "attempted/recorded; use it to ask a specific, informed question rather "
                "than a generic one."
            )

        return CustomerConversationProjection(
            customer_name=ccc.customer_profile.name,
            customer_phone=ccc.customer_profile.phone,
            awb_no=ccc.order_facts.awb_no,
            collectable_amount=ccc.order_facts.collectable_amount,
            payment_mode=ccc.order_facts.payment_mode,
            actual_item_price=ccc.order_facts.actual_item_price,
            order_quantity=ccc.order_facts.order_quantity,
            courier_partner=ccc.order_facts.courier_partner,
            past_delivery_attempts=ccc.order_facts.past_delivery_attempts,
            destination_pincode=ccc.order_facts.destination_pincode,
            prior_communication_summary=ccc.order_facts.prior_communication_summary,
            offered_reattempt_date_1=offered_date_1,
            offered_reattempt_date_2=offered_date_2,
            diagnostic_priority_instruction=diagnostic_priority_instruction,
            product_name=ccc.product_context.product_name,
            product_description=ccc.product_context.product_description,
            product_code=ccc.product_context.product_code,
            sku_id=ccc.product_context.sku_id,
            catalog_selling_price=ccc.product_context.catalog_selling_price,
            mrp=ccc.product_context.mrp,
            image_url=ccc.product_context.image_url,
            size=ccc.product_context.size,
            color=ccc.product_context.color,
            material=ccc.product_context.material,
            features=ccc.product_context.features,
            return_exchange_condition=ccc.product_context.return_exchange_condition,
            attr_style=ccc.product_context.attr_style,
            attr_pattern=ccc.product_context.attr_pattern,
            attr_package_contents=ccc.product_context.attr_package_contents,
            objective=ccc.directive.objective,
            context_summary=ccc.directive.context_summary,
            domain_constraints=ccc.directive.constraints,
            core_safety_constraints=CORE_SAFETY_POLICY,
            # Single authority: the mission's list wins when a mission is attached, so only
            # one allowed-actions list ever reaches the conversational layer.
            allowed_actions=ccc.directive.effective_allowed_actions,
            mission_conversation_mission=mission.conversation_mission if mission else None,
            mission_why_this_call=mission.why_this_call if mission else None,
            mission_primary_objective=mission.primary_objective if mission else None,
            mission_success_condition=mission.success_condition if mission else None,
            mission_initial_state=mission.initial_state if mission else None,
            mission_allowed_next_states=", ".join(mission.allowed_next_states) if mission else None,
            mission_conversation_priority=mission.conversation_priority if mission else None,
            mission_return_to_mission=mission.return_to_mission if mission else None,
        )
