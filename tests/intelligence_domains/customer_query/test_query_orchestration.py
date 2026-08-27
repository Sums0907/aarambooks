import pytest
import json
from unittest.mock import AsyncMock
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.brain_core.action_engine.contracts import ActionCategory
from tests.intelligence_domains.fixtures import normal_customer, normal_order, escalation_customer, high_value_order, missing_order
from src.brain_core.knowledge.interfaces import KnowledgeResult
from src.brain_core.memory.interfaces import MemoryEntry

@pytest.fixture
def mock_gateway():
    return AsyncMock()

@pytest.fixture
def mock_knowledge():
    knowledge = AsyncMock()
    knowledge.search_knowledge.return_value = []
    return knowledge

@pytest.fixture
def mock_memory():
    memory = AsyncMock()
    memory.read_memory.return_value = []
    return memory

@pytest.mark.asyncio
async def test_query_orchestration_status_query(mock_gateway, mock_knowledge, mock_memory):
    llm_output = {
        "intent": "order_status",
        "response_text": "Your order ORD-001 is on the way.",
        "escalation_needed": False,
        "requires_action": False,
        "justification": "Customer wants to know status."
    }
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps(llm_output),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )

    orchestrator = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    response_text, decision, action = await orchestrator.handle_query("Where is my book?", normal_customer, normal_order, session_id="test_session")

    assert response_text == "Your order ORD-001 is on the way."
    assert decision.recommended_alternative_id == "order_status"
    assert action is None
    
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()

@pytest.mark.asyncio
async def test_query_orchestration_escalation(mock_gateway, mock_knowledge, mock_memory):
    llm_output = {
        "intent": "complaint",
        "response_text": "I will get a manager.",
        "escalation_needed": True,
        "requires_action": True,
        "justification": "Customer is VIP and very angry."
    }
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps(llm_output),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )
    
    mock_memory.read_memory.return_value = [MemoryEntry(content="User: I am very angry\nAssistant: Sorry", metadata={})]

    orchestrator = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    response_text, decision, action = await orchestrator.handle_query("I am furious!", escalation_customer, high_value_order, session_id="test_session_2")

    assert action is not None
    assert action.category == ActionCategory.HUMAN_ASSISTANCE
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()

@pytest.mark.asyncio
async def test_query_orchestration_missing_context(mock_gateway, mock_knowledge, mock_memory):
    llm_output = {
        "intent": "order_status",
        "response_text": "I could not find that order.",
        "escalation_needed": False,
        "requires_action": False,
        "justification": "No order context provided."
    }
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps(llm_output),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )

    orchestrator = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    # No session_id provided here
    response_text, decision, action = await orchestrator.handle_query("Where is my order?", normal_customer, missing_order)

    assert response_text == "I could not find that order."
    mock_memory.read_memory.assert_not_called()
    mock_memory.write_memory.assert_not_called()

@pytest.mark.asyncio
async def test_query_orchestration_hallucination_protection(mock_gateway, mock_knowledge, mock_memory):
    # Mocking strict knowledge rule
    mock_knowledge.search_knowledge.return_value = [
        KnowledgeResult(content="NO REFUNDS EVER.", source="policy", confidence_score=1.0, metadata={})
    ]
    
    llm_output = {
        "intent": "refund_request",
        "response_text": "Sorry, no refunds.",
        "escalation_needed": False,
        "requires_action": False,
        "justification": "Policy explicitly states no refunds."
    }
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps(llm_output),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )

    orchestrator = CustomerQueryOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    response_text, decision, action = await orchestrator.handle_query("Give me a refund", normal_customer, normal_order, session_id="test_session_3")

    assert action is None
    assert "no refunds" in response_text.lower()
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()
