import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.brain_core.action_engine.contracts import ActionCategory
from tests.intelligence_domains.fixtures import ndr_shipment, normal_customer, normal_order

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
    decision, action, msg = await orchestrator.orchestrate_resolution(ndr_shipment, normal_customer, normal_order)

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
    decision, action, msg = await orchestrator.orchestrate_resolution(ndr_shipment, normal_customer, normal_order)

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
    decision, action, msg = await orchestrator.orchestrate_resolution(ndr_shipment, normal_customer, normal_order)

    # Verification
    assert msg is None
    assert decision.recommended_alternative_id == "escalate"
    assert action.category == ActionCategory.HUMAN_ASSISTANCE
    
    mock_memory.read_memory.assert_called_once()
    mock_memory.write_memory.assert_called_once()
