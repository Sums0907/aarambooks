import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
    CandidateEntity,
    RefinementContext
)
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding

@pytest.fixture
def mock_classifier():
    classifier = AsyncMock()
    classifier.classify.return_value = ClassifiedRequirement(
        understanding=ConversationalUnderstanding(original_query="test", intent="RETRIEVE", components=[]),
        components=[]
    )
    return classifier

@pytest.fixture
def mock_id_provider():
    provider = AsyncMock()
    provider.extract_understanding.return_value = ConversationalUnderstanding(original_query="test", intent="RETRIEVE", components=[])
    provider.interpret_evidence.return_value = "FINAL_ANSWER"
    return provider

@pytest.fixture
def mock_cem_adapter():
    adapter = AsyncMock()
    return adapter

@pytest.fixture
def orchestrator(mock_id_provider, mock_cem_adapter, mock_classifier):
    id_resolver = MagicMock()
    id_resolver.resolve.return_value = mock_id_provider
    
    cem_resolver = MagicMock()
    cem_resolver.resolve.return_value = mock_cem_adapter
    
    return RabtaOrchestrator(
        id_resolver=id_resolver,
        cem_resolver=cem_resolver,
        classifier=mock_classifier
    )

@pytest.mark.asyncio
async def test_r6_normal_request_one_call(orchestrator, mock_cem_adapter):
    # Pass 1 returns success
    mock_cem_adapter.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"data": "success"}
    )
    
    result = await orchestrator.process_query("test query", "id", "cem", "auth")
    
    assert result == "FINAL_ANSWER"
    assert mock_cem_adapter.execute_evidence_request.call_count == 1

@pytest.mark.asyncio
async def test_r6_multiple_candidates_terminates(orchestrator, mock_cem_adapter, mock_id_provider):
    # Pass 1: Multiple candidates, none are auto-resolved because we don't invent heuristics
    pass_1_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.MULTIPLE_CANDIDATES,
        resolved_candidates={
            "sku": [
                CandidateEntity(semantic_reference="test", business_id="UUID-123", business_name="Item", confidence=1.0),
                CandidateEntity(semantic_reference="test", business_id="UUID-456", business_name="Item2", confidence=0.5)
            ]
        }
    )
    
    mock_cem_adapter.execute_evidence_request.return_value = pass_1_response
    
    result = await orchestrator.process_query("test query", "id", "cem", "auth")
    
    assert result == "FINAL_ANSWER"
    assert mock_cem_adapter.execute_evidence_request.call_count == 1
    
    # Assert it passed the ambiguous response directly to R-8
    assert mock_id_provider.interpret_evidence.call_args[0][0] == pass_1_response

@pytest.mark.asyncio
async def test_r6_entity_not_found_no_second_pass(orchestrator, mock_cem_adapter):
    # Pass 1: Entity Not Found
    pass_1_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.ENTITY_NOT_FOUND
    )
    
    mock_cem_adapter.execute_evidence_request.return_value = pass_1_response
    
    result = await orchestrator.process_query("test query", "id", "cem", "auth")
    
    # Should only call once since safe broadening for NOT_FOUND isn't implemented in this MVP
    assert mock_cem_adapter.execute_evidence_request.call_count == 1
