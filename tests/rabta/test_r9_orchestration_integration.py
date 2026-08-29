import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timezone

from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.shared.rabta_interfaces import IntelligenceDomainResolver, ContextExecutionResolver
from src.brain_core.classification.classifier import RequirementClassifier
from src.shared.conversational_contracts import ConversationalUnderstanding, ConversationalIntent, NormalizedParameter, ParameterDataType, ConversationalResponse, ConversationalResponseType
from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
from src.shared.memory_contracts import SuspendedExecutionState, SuspendedActionStatus
from src.shared.decision_contracts import DecisionStatus
from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.requirement_classification_contracts import ClassifiedRequirement

@pytest.fixture
def mock_id_resolver():
    return MagicMock(spec=IntelligenceDomainResolver)

@pytest.fixture
def mock_cem_resolver():
    return MagicMock(spec=ContextExecutionResolver)

@pytest.fixture
def mock_classifier():
    classifier = AsyncMock(spec=RequirementClassifier)
    classifier.classify.return_value = ClassifiedRequirement(
        understanding=ConversationalUnderstanding(original_query="", intent=ConversationalIntent.ACTION),
        components=[]
    )
    return classifier

@pytest.fixture
def mock_memory():
    memory = AsyncMock()
    memory.read_memory.return_value = []
    memory.suspend_action.return_value = None
    memory.atomic_consume_action.return_value = True
    return memory

@pytest.fixture
def orchestrator(mock_id_resolver, mock_cem_resolver, mock_classifier, mock_memory):
    return RabtaOrchestrator(
        id_resolver=mock_id_resolver,
        cem_resolver=mock_cem_resolver,
        classifier=mock_classifier,
        memory_provider=mock_memory
    )

@pytest.mark.asyncio
async def test_mutative_action_is_suspended_and_not_executed(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="receive goods",
        intent=ConversationalIntent.ACTION
    )
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.CLARIFICATION_REQUIRED,
        message="Confirmation needed"
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem_resolver.resolve.return_value = mock_cem

    result = await orchestrator.process_query(
        query="receive goods",
        id_urn="id:test",
        cem_urn="cem:test",
        auth_context="token",
        session_id="sess_1"
    )

    assert result.response_type == ConversationalResponseType.CLARIFICATION_REQUIRED
    assert mock_cem.execute_evidence_request.call_count == 0
    assert orchestrator._memory_provider.suspend_action.call_count == 1

@pytest.mark.asyncio
async def test_explicit_confirmation_consumes_and_executes(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="yes",
        intent=ConversationalIntent.CONFIRMATION,
        parameters=[NormalizedParameter(parameter_name="nonce", data_type=ParameterDataType.STRING, value="nonce_1", original_expression="nonce_1")]
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem.execute_evidence_request.return_value = BusinessEvidenceResponse(status=BusinessRealityStatus.CAPABILITY_AVAILABLE)
    mock_cem_resolver.resolve.return_value = mock_cem
    
    # Mock R-8 interpretation
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="Executed"
    )

    req = AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(original_query="receive", intent=ConversationalIntent.ACTION),
            components=[]
        )
    )
    state = SuspendedExecutionState(
        nonce="nonce_1",
        session_id="sess_1",
        request=req,
        status=SuspendedActionStatus.PENDING,
        expires_at=datetime.now(timezone.utc)
    )
    orchestrator._memory_provider.retrieve_suspended_action.return_value = state
    orchestrator._memory_provider.atomic_consume_action.return_value = True

    result = await orchestrator.process_query("yes", "id:test", "cem:test", "auth", "sess_1")

    assert mock_cem.execute_evidence_request.call_count == 1
    assert orchestrator._memory_provider.atomic_consume_action.call_count == 1
    # Check that it executed the original request, not the "yes" intent request
    executed_req = mock_cem.execute_evidence_request.call_args[0][0]
    assert executed_req.classified_requirement.understanding.intent == ConversationalIntent.ACTION

@pytest.mark.asyncio
async def test_duplicate_confirmation_does_not_execute(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="yes",
        intent=ConversationalIntent.CONFIRMATION,
        parameters=[NormalizedParameter(parameter_name="nonce", data_type=ParameterDataType.STRING, value="nonce_1", original_expression="nonce_1")]
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem_resolver.resolve.return_value = mock_cem
    
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.EXECUTION_LIMITATION,
        message="Action rejected"
    )

    req = AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(original_query="receive", intent=ConversationalIntent.ACTION),
            components=[]
        )
    )
    state = SuspendedExecutionState(
        nonce="nonce_1",
        session_id="sess_1",
        request=req,
        status=SuspendedActionStatus.PENDING,
        expires_at=datetime.now(timezone.utc)
    )
    orchestrator._memory_provider.retrieve_suspended_action.return_value = state
    
    # Second time, atomic consume fails
    orchestrator._memory_provider.atomic_consume_action.return_value = False

    result = await orchestrator.process_query("yes", "id:test", "cem:test", "auth", "sess_1")

    assert mock_cem.execute_evidence_request.call_count == 0
    assert result.response_type == ConversationalResponseType.EXECUTION_LIMITATION

@pytest.mark.asyncio
async def test_explicit_rejection_does_not_execute(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="no",
        intent=ConversationalIntent.REJECTION,
        parameters=[NormalizedParameter(parameter_name="nonce", data_type=ParameterDataType.STRING, value="nonce_1", original_expression="nonce_1")]
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem_resolver.resolve.return_value = mock_cem
    
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.EXECUTION_LIMITATION,
        message="Cancelled"
    )

    orchestrator._memory_provider.retrieve_suspended_action.return_value = SuspendedExecutionState(
        nonce="nonce_1", session_id="sess_1", 
        request=AbstractEvidenceRequest(classified_requirement=ClassifiedRequirement(understanding=ConversationalUnderstanding(original_query="", intent=ConversationalIntent.ACTION), components=[])),
        status=SuspendedActionStatus.PENDING, expires_at=datetime.now(timezone.utc)
    )
    orchestrator._memory_provider.atomic_consume_action.return_value = True

    result = await orchestrator.process_query("no", "id:test", "cem:test", "auth", "sess_1")

    assert mock_cem.execute_evidence_request.call_count == 0
    assert orchestrator._memory_provider.atomic_consume_action.call_count == 1

@pytest.mark.asyncio
async def test_unrelated_query_leaves_suspended_action_untouched(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="search",
        intent=ConversationalIntent.SEARCH
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem.execute_evidence_request.return_value = BusinessEvidenceResponse(status=BusinessRealityStatus.CAPABILITY_AVAILABLE)
    mock_cem_resolver.resolve.return_value = mock_cem
    
    mock_classifier = AsyncMock()
    mock_classifier.classify.return_value = ClassifiedRequirement(
        understanding=ConversationalUnderstanding(original_query="search", intent=ConversationalIntent.SEARCH),
        components=[]
    )
    orchestrator._classifier = mock_classifier
    
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="Found"
    )

    result = await orchestrator.process_query("search", "id:test", "cem:test", "auth", "sess_1")

    assert mock_cem.execute_evidence_request.call_count == 1
    assert orchestrator._memory_provider.atomic_consume_action.call_count == 0

@pytest.mark.asyncio
async def test_proactive_recommendation_generated_and_suspended(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="check exceptions",
        intent=ConversationalIntent.RETRIEVE
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"items": [{"open_exceptions": 2}]}
    )
    mock_cem_resolver.resolve.return_value = mock_cem
    
    mock_classifier = AsyncMock()
    mock_classifier.classify.return_value = ClassifiedRequirement(
        understanding=ConversationalUnderstanding(original_query="check exceptions", intent=ConversationalIntent.RETRIEVE),
        components=[]
    )
    orchestrator._classifier = mock_classifier
    
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="Found 2 exceptions"
    )

    result = await orchestrator.process_query("check exceptions", "id:test", "cem:test", "auth", "sess_1")

    assert mock_cem.execute_evidence_request.call_count == 1
    assert orchestrator._memory_provider.suspend_action.call_count == 1
    assert hasattr(result, "recommendations")
    assert len(result.recommendations) == 1
    assert result.recommendations[0]["action_type"] == "RESOLVE_EXCEPTIONS"

@pytest.mark.asyncio
async def test_no_recommendation_when_evidence_insufficient(orchestrator, mock_id_resolver, mock_cem_resolver):
    mock_id = AsyncMock()
    mock_id.extract_understanding.return_value = ConversationalUnderstanding(
        original_query="check exceptions",
        intent=ConversationalIntent.RETRIEVE
    )
    mock_id_resolver.resolve.return_value = mock_id

    mock_cem = AsyncMock()
    mock_cem.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"items": [{"open_exceptions": 0}]}
    )
    mock_cem_resolver.resolve.return_value = mock_cem
    
    mock_classifier = AsyncMock()
    mock_classifier.classify.return_value = ClassifiedRequirement(
        understanding=ConversationalUnderstanding(original_query="check exceptions", intent=ConversationalIntent.RETRIEVE),
        components=[]
    )
    orchestrator._classifier = mock_classifier
    
    mock_id.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="Found 0 exceptions"
    )

    result = await orchestrator.process_query("check exceptions", "id:test", "cem:test", "auth", "sess_1")

    assert mock_cem.execute_evidence_request.call_count == 1
    assert orchestrator._memory_provider.suspend_action.call_count == 0
    assert not getattr(result, "recommendations", None)
