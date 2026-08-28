import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.brain_core.action_engine.contracts import ActionCategory
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata
from src.brain_core.knowledge.interfaces import KnowledgeResult
from src.brain_core.memory.interfaces import MemoryEntry

def create_ndr_evidence_package(shipment_data: dict, customer_data: dict, order_data: dict = None) -> EvidencePackage:
    payload = {
        "shipment_context": shipment_data,
        "customer_context": customer_data,
    }
    if order_data:
        payload["order_context"] = order_data
        
    item = EvidenceItem(
        item_id=str(uuid.uuid4()),
        semantic_identity="ndr_update",
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
    gateway = AsyncMock()
    return gateway

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
async def test_ndr_orchestration_happy_path(mock_gateway, mock_knowledge, mock_memory):
    # Setup mock LLM response
    llm_output = {
        "intent": "reschedule_delivery",
        "customer_message": "Would you like us to reattempt delivery tomorrow?",
        "escalation_needed": False,
        "action_category": "suggested_resolution",
        "justification": "Customer was not available on first attempt. Standard policy allows retry."
    }
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps(llm_output),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )

    orchestrator = NDRIntelligenceOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    pkg = create_ndr_evidence_package({"shipment_id": "SHIP-001"}, {"customer_id": "C123"})
    decision, action, msg = await orchestrator.orchestrate_resolution(pkg)

    # Verification
    assert msg == "Would you like us to reattempt delivery tomorrow?"
    assert decision.recommended_alternative_id == "reschedule_delivery"
    assert action.category == ActionCategory.SUGGESTED_RESOLUTION
    assert action.parameters["shipment_id"] == "SHIP-001"
    
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()

@pytest.mark.asyncio
async def test_ndr_orchestration_escalation(mock_gateway, mock_knowledge, mock_memory):
    # Setup mock LLM response for escalation
    llm_output = {
        "intent": "escalate",
        "customer_message": "An agent will contact you.",
        "escalation_needed": True,
        "action_category": "human_assistance",
        "justification": "Courier marked as fake attempt, human review needed."
    }
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content=json.dumps(llm_output),
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )

    orchestrator = NDRIntelligenceOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    pkg = create_ndr_evidence_package({"shipment_id": "SHIP-002"}, {"customer_id": "C123"})
    decision, action, msg = await orchestrator.orchestrate_resolution(pkg)

    # Verification
    assert decision.recommended_alternative_id == "escalate"
    assert action.category == ActionCategory.HUMAN_ASSISTANCE
    
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()

@pytest.mark.asyncio
async def test_ndr_orchestration_parse_failure(mock_gateway, mock_knowledge, mock_memory):
    # Setup mock LLM response that fails to parse
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content="This is not valid JSON",
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=10
    )

    orchestrator = NDRIntelligenceOrchestrator(gateway=mock_gateway, knowledge=mock_knowledge, memory=mock_memory)
    pkg = create_ndr_evidence_package({"shipment_id": "SHIP-003"}, {"customer_id": "C123"})
    decision, action, msg = await orchestrator.orchestrate_resolution(pkg)

    # Verification
    assert msg is None
    assert decision.recommended_alternative_id == "escalate"
    assert action.category == ActionCategory.HUMAN_ASSISTANCE
    
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()
