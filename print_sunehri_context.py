import asyncio
from unittest.mock import AsyncMock

from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ExecutionIntent, ExecutionChannel
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.brain_core.context_engine.ccc_contracts import ConversationalDirective
from src.api.webhooks.exotel_webhooks import generate_dynamic_greeting

async def main():
    from src.shared.evidence_request_contracts import BusinessRealityStatus
    mock_adapter = AsyncMock()
    mock_adapter.execute_evidence_request.return_value = type("MockResponse", (), {
        "status": BusinessRealityStatus.EVIDENCE_AVAILABLE,
        "evidence_data": {
            "customer_name": "Priya Sharma",
            "customer.attribute.phone": "+919876543210",
            "cod_amount": 2500,
            "payment_mode": "PREPAID",
            "items": [{
                "sku_id": "SKU123",
                "product_code": "PC123",
                "product_name": "Premium Cotton Bedsheet",
                "quantity": 1,
                "selling_price": 2500, "mrp": 3999, "image_url": "https://example.com/img.jpg", "size": "King", "color": "Blue", "return_exchange_condition": "7 days return", "attr_style": "Modern", "attr_pattern": "Solid", "attr_package_contents": "1 Bedsheet, 2 Pillow Covers"
            }]
        }
    })()

    mock_inventory = AsyncMock()
    mock_inventory.execute_evidence_request.return_value = type("MockResponse", (), {
        "status": BusinessRealityStatus.EVIDENCE_AVAILABLE,
        "evidence_data": {
            "product_name": "Premium Cotton Bedsheet (Inventory DB)",
            "description": "Rich 100% Egyptian Cotton, 400 TC, Machine Washable.",
            "selling_price": 2400.0,
            "mrp": 3999.0,
            "image_url": "https://s3.ap-south-1.amazonaws.com/nushop-catalogue/mock-image.png",
            "size": "King Size",
            "color": "Blush Pink",
            "return_exchange_condition": "7 Days Return",
            "attr_style": "Modern",
            "attr_pattern": "Floral",
            "attr_package_contents": "1 Bedsheet, 2 Pillow Covers"
        }
    })()

    builder = CustomerConversationContextBuilder(provider=mock_adapter, inventory_provider=mock_inventory)
    
    # Mock NDR directive
    directive = ConversationalDirective(
        objective="Secure customer confirmation for delivery reattempt.",
        context_summary="Delivery failed today due to customer unavailability.",
        allowed_actions=["reschedule"],
        constraints=["Do not mention courier", "Only offer tomorrow as an option"]
    )
    
    action = ActionRequest(
        action_request_id="act_test_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test strategy",
        parameters={"customer_phone": "+919876543210", "awb_no": "370909749714"},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
        directive=directive
    )
    
    # Build CCC
    ccc = await builder.build(action)
    print("\n=== FULL IMMUTABLE CCC SNAPSHOT ===")
    import json
    print(json.dumps(ccc.model_dump(), indent=2))
    
    # Project
    projection = builder.project(ccc)
    print("\n=== CUSTOMER CONVERSATION PROJECTION ===")
    print(json.dumps(projection.model_dump(), indent=2))
    
    # Map to Exotel session constants (simulating exotel_webhooks.py logic)
    session_constants = {
        "brand_name": "Aaram Homes",
        "engagement_id": "eng_test_123",
        "action_request_id": "act_test_123",
    }
    call_context = projection.model_dump()
    for key in call_context.keys():
        if call_context.get(key) is not None:
            if isinstance(call_context[key], list):
                session_constants[key] = ", ".join(call_context[key])
            else:
                session_constants[key] = str(call_context[key])
                
    print("\n=== FINAL SUNEHRI EXOTEL SESSION CONSTANTS ===")
    print(json.dumps(session_constants, indent=2))
    
    # Generate dynamic greeting
    mock_engagement = {"call_context": call_context}
    greeting = generate_dynamic_greeting(mock_engagement)
    print("\n=== DYNAMIC GREETING GENERATED AT SESSION START ===")
    print(greeting)

if __name__ == "__main__":
    asyncio.run(main())
