import pytest
import json
from unittest.mock import AsyncMock
from src.event_bus.receiver import InboundReceiver
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse

@pytest.fixture
def mock_gateway():
    gateway = AsyncMock()
    gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps({
            "intent": "status_query",
            "customer_message": "Your order is in transit.",
            "escalation_needed": False,
            "requires_action": True,
            "action_category": "information_provided",
            "justification": "Tracking says transit"
        }),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )
    return gateway

@pytest.fixture
def mock_knowledge():
    k = AsyncMock()
    k.search_knowledge.return_value = []
    return k

@pytest.fixture
def mock_memory():
    m = AsyncMock()
    m.read_memory.return_value = []
    return m

@pytest.mark.asyncio
async def test_logical_e2e_customer_query(mock_gateway, mock_knowledge, mock_memory):
    """
    LOGICAL E2E TEST: Tests the entire path from InboundReceiver, through the CustomerQueryOrchestrator,
    and out via the OutboundDispatcher. Uses mocked physical dependencies.
    """
    query_orch = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    ndr_orch = NDRIntelligenceOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    
    receiver = InboundReceiver(query_orch, ndr_orch)
    
    payload = {
        "event_type": "customer_query",
        "content": {
            "query_text": "Where is my order?",
            "customer_context": {"customer_id": "C123"},
            "session_id": "e2e_session"
        }
    }
    
    dispatched_str = await receiver.process_raw_payload(json.dumps(payload))
    
    assert dispatched_str is not None
    action_dict = json.loads(dispatched_str)
    
    assert action_dict["event_type"] == "action_dispatched"
    assert action_dict["payload"]["category"] == "suggested_resolution"
    mock_memory.write_memory.assert_called_once()

@pytest.mark.asyncio
async def test_logical_e2e_ndr_update(mock_gateway, mock_knowledge, mock_memory):
    """
    LOGICAL E2E TEST: Tests the entire path from InboundReceiver to ActionRequest serialization for NDR events.
    """
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps({
            "intent": "reschedule",
            "customer_message": "Can we deliver tomorrow?",
            "escalation_needed": False,
            "action_category": "suggested_resolution",
            "justification": "Standard reschedule"
        }),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )
    
    query_orch = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    ndr_orch = NDRIntelligenceOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    
    receiver = InboundReceiver(query_orch, ndr_orch)
    
    payload = {
        "event_type": "ndr_update",
        "content": {
            "shipment_context": {"shipment_id": "S123", "awb_no": "A123", "status": "NDR", "courier": "DHL"},
            "customer_context": {"customer_id": "C123"}
        }
    }
    
    dispatched_str = await receiver.process_raw_payload(json.dumps(payload))
    
    assert dispatched_str is not None
    action_dict = json.loads(dispatched_str)
    
    assert action_dict["event_type"] == "action_dispatched"
    assert action_dict["payload"]["category"] == "suggested_resolution"
    mock_memory.write_memory.assert_called_once()
