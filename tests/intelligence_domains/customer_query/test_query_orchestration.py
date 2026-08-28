import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.brain_core.action_engine.contracts import ActionCategory
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata
from src.brain_core.knowledge.interfaces import KnowledgeResult
from src.brain_core.memory.interfaces import MemoryEntry

def create_evidence_package(query_text: str, session_id: str, customer_data: dict, order_data: dict = None) -> EvidencePackage:
    payload = {
        "query_text": query_text,
        "session_id": session_id,
        "customer_context": customer_data,
    }
    if order_data:
        payload["order_context"] = order_data
        
    item = EvidenceItem(
        item_id=str(uuid.uuid4()),
        semantic_identity="customer_query",
        data_payload=payload,
        provenance=ProvenanceMetadata(
            retrieval_timestamp=datetime.now(timezone.utc),
            derivation_metadata="test"
        )
    )
    return EvidencePackage(
        package_id=str(uuid.uuid4()),
        plan_id="test",
        evidence_items=[item],
        sufficiency_assessment="SUFFICIENT"
    )

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
    pkg = create_evidence_package("Where is my book?", "test_session", {"customer_id": "cust1"}, {"order_id": "ord1"})
    response_text, decision, action = await orchestrator.handle_query(pkg)

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
    pkg = create_evidence_package("I am furious!", "test_session_2", {"customer_id": "cust_esc"}, {"order_id": "ord_high"})
    response_text, decision, action = await orchestrator.handle_query(pkg)

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
    pkg = create_evidence_package("Where is my order?", None, {"customer_id": "cust1"}, None)
    response_text, decision, action = await orchestrator.handle_query(pkg)

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
    pkg = create_evidence_package("Give me a refund", "test_session_3", {"customer_id": "cust1"}, {"order_id": "ord1"})
    response_text, decision, action = await orchestrator.handle_query(pkg)

    assert action is None
    assert "no refunds" in response_text.lower()
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()
