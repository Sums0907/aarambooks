import uuid
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
            past_delivery_attempts=evidence.get("ndr_count")
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
                past_delivery_attempts=order_ctx.past_delivery_attempts
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
            allowed_actions=ccc.directive.allowed_actions
        )
