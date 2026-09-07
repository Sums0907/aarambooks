import asyncio
import json
import sys
import traceback
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ExecutionIntent, ExecutionChannel
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.brain_core.context_engine.ccc_contracts import ConversationalDirective
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.infrastructure.adapters.inventory_cem_adapter import InventoryCemAdapter
from src.shared.config import settings

async def main():
    awb_no = sys.argv[1] if len(sys.argv) > 1 else "142285239995710"
    shopdeck_cem = ShopdeckCemAdapter(base_url=getattr(settings, "shopdeck_url", "http://localhost:8200"))
    inventory_cem = InventoryCemAdapter(brain_orchestrator=None, capabilities=[])
    builder = CustomerConversationContextBuilder(provider=shopdeck_cem, inventory_provider=inventory_cem)
    
    directive = ConversationalDirective(
        objective="Secure customer confirmation for delivery reattempt.",
        context_summary="Delivery failed today due to customer unavailability.",
        allowed_actions=["reschedule"],
        constraints=["Do not mention courier", "Only offer tomorrow as an option"]
    )
    
    action = ActionRequest(
        action_request_id="act_real_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test strategy",
        parameters={"customer_phone": "+919876543210", "awb_no": awb_no},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
        directive=directive
    )
    
    try:
        ccc = await builder.build(action)
        projection = builder.project(ccc)
        call_context = projection.model_dump()
        session_constants = {}
        for key in call_context.keys():
            if call_context.get(key) is not None:
                if isinstance(call_context[key], list):
                    session_constants[key] = ", ".join(call_context[key])
                else:
                    session_constants[key] = str(call_context[key])
        print(json.dumps(session_constants, indent=2))
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
