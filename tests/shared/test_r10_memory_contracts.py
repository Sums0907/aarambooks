import pytest
from datetime import datetime, timedelta, timezone
import json
from src.shared.memory_contracts import (
    ConversationTurn, 
    SuspendedExecutionState, 
    SuspendedActionStatus
)
from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.requirement_classification_contracts import ClassifiedRequirement, RequirementClass
from src.shared.conversational_contracts import ConversationalResponse, ConversationalResponseType, ConversationalUnderstanding, ConversationalIntent

def test_conversation_turn_valid():
    response = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="Hello"
    )
    turn = ConversationTurn(
        turn_id="t-1",
        session_id="s-1",
        user_utterance="hi",
        system_response=response
    )
    assert turn.turn_id == "t-1"
    assert turn.session_id == "s-1"
    assert turn.user_utterance == "hi"

def _get_req():
    u = ConversationalUnderstanding(intent=ConversationalIntent.ACTION, original_query="receive")
    c = ClassifiedRequirement(understanding=u, global_classification=RequirementClass.MANDATORY)
    return AbstractEvidenceRequest(classified_requirement=c)

def test_suspended_execution_state_valid():
    req = _get_req()
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    state = SuspendedExecutionState(
        nonce="n-123",
        session_id="s-1",
        request=req,
        expires_at=expires
    )
    
    assert state.nonce == "n-123"
    assert state.session_id == "s-1"
    assert state.status == SuspendedActionStatus.PENDING

def test_serialization_and_deserialization():
    req = _get_req()
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    state = SuspendedExecutionState(
        nonce="n-123",
        session_id="s-1",
        request=req,
        expires_at=expires
    )
    
    json_data = state.model_dump_json()
    assert isinstance(json_data, str)
    
    loaded_state = SuspendedExecutionState.model_validate_json(json_data)
    assert loaded_state.nonce == state.nonce
    assert loaded_state.session_id == state.session_id
    assert loaded_state.request.classified_requirement.global_classification == RequirementClass.MANDATORY

def test_malformed_state_rejection():
    bad_json = '{"nonce": "n-1", "session_id": "s-1", "missing_request_and_expires": true}'
    with pytest.raises(Exception):
        SuspendedExecutionState.model_validate_json(bad_json)
