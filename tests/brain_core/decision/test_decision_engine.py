import pytest
from unittest.mock import AsyncMock
import uuid
from src.brain_core.decision.decision_engine import DecisionEngine
from src.shared.decision_contracts import DecisionStatus
from src.shared.conversational_contracts import ConversationalIntent, ConversationalUnderstanding
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.memory_contracts import SuspendedExecutionState, SuspendedActionStatus
from datetime import datetime, timezone

def create_mock_request(intent: ConversationalIntent):
    return AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(
                original_query="query",
                intent=intent,
                components=[]
            ),
            components=[]
        )
    )

@pytest.fixture
def mock_memory():
    memory = AsyncMock()
    return memory

@pytest.fixture
def engine(mock_memory):
    return DecisionEngine(memory_provider=mock_memory)

@pytest.mark.asyncio
async def test_mutative_request_requires_confirmation(engine, mock_memory):
    req = create_mock_request(ConversationalIntent.ACTION)
    res = await engine.evaluate_request(req, "sess-1")
    
    assert res.status == DecisionStatus.CONFIRMATION_REQUIRED
    assert res.confirmation_context is not None
    assert mock_memory.suspend_action.call_count == 1
    
    state_saved = mock_memory.suspend_action.call_args[0][0]
    assert state_saved.nonce == res.confirmation_context.nonce
    assert state_saved.session_id == "sess-1"

@pytest.mark.asyncio
async def test_non_mutative_request_proceeds(engine, mock_memory):
    req = create_mock_request(ConversationalIntent.RETRIEVE)
    res = await engine.evaluate_request(req, "sess-1")
    
    assert res.status == DecisionStatus.PROCEED
    assert mock_memory.suspend_action.call_count == 0

@pytest.mark.asyncio
async def test_explicit_confirmation_consumes_exactly_once(engine, mock_memory):
    req = create_mock_request(ConversationalIntent.ACTION)
    mock_memory.retrieve_suspended_action.return_value = SuspendedExecutionState(
        nonce="nonce-1", session_id="sess-1", request=req, status=SuspendedActionStatus.PENDING, expires_at=datetime.now(timezone.utc)
    )
    mock_memory.atomic_consume_action.return_value = True
    
    res = await engine.process_intent(ConversationalIntent.CONFIRMATION, "sess-1", "nonce-1")
    
    assert res.status == DecisionStatus.CONFIRMED
    assert res.confirmation_context is not None
    assert mock_memory.atomic_consume_action.call_count == 1

@pytest.mark.asyncio
async def test_second_confirmation_cannot_consume(engine, mock_memory):
    req = create_mock_request(ConversationalIntent.ACTION)
    mock_memory.retrieve_suspended_action.return_value = SuspendedExecutionState(
        nonce="nonce-1", session_id="sess-1", request=req, status=SuspendedActionStatus.PENDING, expires_at=datetime.now(timezone.utc)
    )
    mock_memory.atomic_consume_action.return_value = False
    
    res = await engine.process_intent(ConversationalIntent.CONFIRMATION, "sess-1", "nonce-1")
    
    assert res.status == DecisionStatus.REJECTED

@pytest.mark.asyncio
async def test_explicit_rejection_does_not_execute(engine, mock_memory):
    req = create_mock_request(ConversationalIntent.ACTION)
    mock_memory.retrieve_suspended_action.return_value = SuspendedExecutionState(
        nonce="nonce-1", session_id="sess-1", request=req, status=SuspendedActionStatus.PENDING, expires_at=datetime.now(timezone.utc)
    )
    mock_memory.atomic_consume_action.return_value = True
    
    res = await engine.process_intent(ConversationalIntent.REJECTION, "sess-1", "nonce-1")
    
    assert res.status == DecisionStatus.REJECTED
    assert mock_memory.atomic_consume_action.call_count == 1

@pytest.mark.asyncio
async def test_unrelated_query_leaves_pending_intact(engine, mock_memory):
    res = await engine.process_intent(ConversationalIntent.RETRIEVE, "sess-1", "nonce-1")
    
    assert res.status == DecisionStatus.PROCEED
    assert mock_memory.atomic_consume_action.call_count == 0
    assert mock_memory.retrieve_suspended_action.call_count == 0

@pytest.mark.asyncio
async def test_ambiguous_confirmation_does_not_execute(engine, mock_memory):
    res = await engine.process_intent(ConversationalIntent.UNKNOWN, "sess-1", "nonce-1")
    
    assert res.status == DecisionStatus.PROCEED
    assert mock_memory.atomic_consume_action.call_count == 0
    assert mock_memory.retrieve_suspended_action.call_count == 0

@pytest.mark.asyncio
async def test_expired_or_missing_state_rejects(engine, mock_memory):
    mock_memory.retrieve_suspended_action.return_value = None
    
    res = await engine.process_intent(ConversationalIntent.CONFIRMATION, "sess-1", "nonce-1")
    
    assert res.status == DecisionStatus.REJECTED
