import pytest
import json
from unittest.mock import AsyncMock
from src.event_bus.receiver import InboundReceiver
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from httpx import TimeoutException

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
async def test_chaos_llm_timeout(mock_knowledge, mock_memory):
    """
    CHAOS TEST: Simulates a Gateway/LLM timeout to verify controlled escalation.
    """
    gateway_timeout = AsyncMock()
    gateway_timeout.generate.side_effect = TimeoutException("LLM Gateway Timeout")
    
    query_orch = CustomerQueryOrchestrator(gateway=gateway_timeout, knowledge=mock_knowledge, memory=mock_memory)
    ndr_orch = NDRIntelligenceOrchestrator(gateway=gateway_timeout, knowledge=mock_knowledge, memory=mock_memory)
    receiver = InboundReceiver(query_orch, ndr_orch)
    
    payload = {
        "event_type": "customer_query",
        "content": {
            "query_text": "Where is my order?",
            "customer_context": {"customer_id": "C123"}
        }
    }
    
    with pytest.raises(TimeoutException):
        await receiver.process_raw_payload(json.dumps(payload))

@pytest.mark.asyncio
async def test_chaos_memory_failure():
    """
    CHAOS TEST: Simulates a Database/Memory Provider failure.
    """
    mock_gateway = AsyncMock()
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps({"intent": "query", "action_category": "human_assistance", "justification": ""}),
        model_used="test", prompt_tokens=0, completion_tokens=0
    )
    mock_knowledge = AsyncMock()
    
    memory_failure = AsyncMock()
    memory_failure.read_memory.side_effect = Exception("Database Connection Lost")
    
    query_orch = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=memory_failure)
    ndr_orch = NDRIntelligenceOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=memory_failure)
    receiver = InboundReceiver(query_orch, ndr_orch)
    
    payload = {
        "event_type": "customer_query",
        "content": {
            "query_text": "Where is my order?",
            "customer_context": {"customer_id": "C123"},
            "session_id": "fail_session"
        }
    }
    
    with pytest.raises(Exception, match="Database Connection Lost"):
        await receiver.process_raw_payload(json.dumps(payload))
