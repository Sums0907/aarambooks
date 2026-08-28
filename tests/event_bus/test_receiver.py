import pytest
import json
from src.event_bus.receiver import InboundReceiver
from src.security.validator import SecurityValidationError
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory

class FakeQueryOrchestrator:
    async def handle_query(self, **kwargs):
        return ("Hello", None, ActionRequest(category=ActionCategory.HUMAN_ASSISTANCE, reasoning="test", parameters={}))

class FakeNDROrchestrator:
    async def orchestrate_resolution(self, **kwargs):
        return (None, ActionRequest(category=ActionCategory.SUGGESTED_RESOLUTION, reasoning="ndr", parameters={}), None)

@pytest.fixture
def mock_query_orchestrator():
    return FakeQueryOrchestrator()

@pytest.fixture
def mock_ndr_orchestrator():
    return FakeNDROrchestrator()

@pytest.mark.asyncio
async def test_receiver_valid_customer_query(mock_query_orchestrator, mock_ndr_orchestrator):
    receiver = InboundReceiver(mock_query_orchestrator, mock_ndr_orchestrator)
    
    payload = {
        "event_type": "customer_query",
        "content": {
            "query_text": "Hello",
            "customer_context": {"customer_id": "C123"},
            "session_id": "session123"
        }
    }
    
    result = await receiver.process_raw_payload(json.dumps(payload))
    
    assert result is not None
    parsed_result = json.loads(result)
    assert parsed_result["event_type"] == "action_dispatched"

@pytest.mark.asyncio
async def test_receiver_valid_ndr(mock_query_orchestrator, mock_ndr_orchestrator):
    receiver = InboundReceiver(mock_query_orchestrator, mock_ndr_orchestrator)
    
    payload = {
        "event_type": "ndr_update",
        "content": {
            "shipment_context": {"shipment_id": "S123", "awb_no": "A123", "status": "NDR", "courier": "DHL"},
            "customer_context": {"customer_id": "C123"}
        }
    }
    
    result = await receiver.process_raw_payload(json.dumps(payload))
    
    assert result is not None
    parsed_result = json.loads(result)
    assert parsed_result["payload"]["category"] == ActionCategory.SUGGESTED_RESOLUTION.value
