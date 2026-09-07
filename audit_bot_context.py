import asyncio
import json
import sys
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.infrastructure.adapters.inventory_cem_adapter import InventoryCemAdapter
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ExecutionIntent, ExecutionChannel
from src.brain_core.context_engine.ccc_contracts import ConversationalDirective
from src.api.webhooks.exotel_webhooks import generate_dynamic_greeting
from src.shared.config import settings

async def main():
    awb_no = "142285201228553"
    if len(sys.argv) > 1:
        awb_no = sys.argv[1]
        
    print(f"==================================================")
    print(f"🔍 AUDIT MODE: FETCHING REAL NDR FOR AWB {awb_no}")
    print(f"==================================================")
    
    # Initialize real adapters
    shopdeck_adapter = ShopdeckCemAdapter(base_url=settings.shopdeck_url)
    inventory_adapter = InventoryCemAdapter(brain_orchestrator=None, capabilities=[])
    
    builder = CustomerConversationContextBuilder(
        provider=shopdeck_adapter, 
        inventory_provider=inventory_adapter
    )
    
    # Create the action request exactly as the Orchestrator would
    directive = ConversationalDirective(
        objective="Secure customer confirmation for delivery reattempt.",
        context_summary="Delivery failed today due to customer unavailability.",
        allowed_actions=["reschedule"],
        constraints=["Do not mention courier", "Only offer tomorrow as an option"]
    )
    
    action = ActionRequest(
        action_request_id="audit_act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Dry run testing",
        parameters={"awb_no": awb_no},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
        directive=directive
    )
    
    print("\n[1] Fetching evidence from real ShopDeck and Inventory...")
    try:
        ccc = await builder.build(action)
    except Exception as e:
        print(f"\n❌ FAILED to build CCC: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    print("\n[2] CCC built successfully. Projecting for Exotel VoiceBot...")
    projection = builder.project(ccc)
    
    print("\n=== FINAL PRIYA EXOTEL SESSION CONSTANTS ===")
    session_constants = {
        "brand_name": "Aaram Homes",
        "engagement_id": "audit_eng_123",
        "action_request_id": "audit_act_123",
    }
    call_context = projection.model_dump()
    for key in call_context.keys():
        if call_context.get(key) is not None:
            if isinstance(call_context[key], list):
                session_constants[key] = ", ".join(call_context[key])
            else:
                session_constants[key] = str(call_context[key])
                
    print(json.dumps(session_constants, indent=2))
    
    print("\n=== DYNAMIC GREETING (FIRST BOT UTTERANCE) ===")
    mock_engagement = {"call_context": call_context}
    greeting = generate_dynamic_greeting(mock_engagement)
    print(greeting)
    
    print("\n✅ AUDIT COMPLETE. No physical call was made.")

if __name__ == "__main__":
    asyncio.run(main())
