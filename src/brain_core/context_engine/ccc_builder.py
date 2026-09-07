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
            order_value=float(evidence.get("cod_amount") or 0.0),
            payment_mode=evidence.get("payment_mode", "UNKNOWN")
        )
        
        # 3. Hydrate Product Context
        items = evidence.get("items", [])
        if items and len(items) > 0:
            first_item = items[0]
            sku_id = first_item.get("sku_id")
            
            product_description = None
            rich_attributes_available = False
            
            # Fetch enriched description from Inventory BS
            if sku_id and self.inventory_provider:
                inv_req = AbstractEvidenceRequest(
                    classified_requirement=ClassifiedRequirement(
                        understanding=ConversationalUnderstanding(
                            intent="SEARCH",
                            original_query=f"Get details for {sku_id}",
                            entities=[SemanticEntityReference(inferred_type="item_code", original_expression=sku_id)]
                        )
                    )
                )
                inv_response = await self.inventory_provider.execute_evidence_request(inv_req, "")
                if inv_response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE and inv_response.evidence_data:
                    inv_data = inv_response.evidence_data
                    product_description = inv_data.get("description")
                    # If Inventory provides a richer product_name, prefer it
                    if inv_data.get("product_name") and not first_item.get("product_name"):
                        first_item["product_name"] = inv_data["product_name"]
                    rich_attributes_available = True
            
            product_ctx = ProductContext(
                sku_id=sku_id,
                product_code=first_item.get("product_code"),
                product_name=first_item.get("product_name"),
                product_description=product_description,
                quantity=first_item.get("quantity"),
                selling_price=float(first_item.get("selling_price", 0.0)),
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
        Projects the full CCC into a governed, customer-safe subset for SUNEHRI LLM consumption.
        Strips away all internal IDs and focuses purely on conversational facts.
        Injects immutable Core Safety Policy independent of Domain directives.
        """
        CORE_SAFETY_POLICY = [
            "Never execute a financial transaction.",
            "Do not disclose internal system IDs or logic.",
            "Do not invent unauthoritative products, names, or reasons."
        ]

        return CustomerConversationProjection(
            customer_name=ccc.customer_profile.name,
            customer_phone=ccc.customer_profile.phone,
            awb_no=ccc.order_facts.awb_no,
            order_value=ccc.order_facts.order_value,
            payment_mode=ccc.order_facts.payment_mode,
            product_name=ccc.product_context.product_name,
            product_description=ccc.product_context.product_description,
            quantity=ccc.product_context.quantity,
            objective=ccc.directive.objective,
            context_summary=ccc.directive.context_summary,
            domain_constraints=ccc.directive.constraints,
            core_safety_constraints=CORE_SAFETY_POLICY,
            allowed_actions=ccc.directive.allowed_actions
        )
