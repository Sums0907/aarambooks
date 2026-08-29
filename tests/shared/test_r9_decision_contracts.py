import pytest
from pydantic import ValidationError
import uuid
from src.shared.decision_contracts import (
    DecisionResponse,
    DecisionStatus,
    ConfirmationRequired,
    Recommendation
)
from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding, ConversationalIntent

def create_mock_request():
    return AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(
                original_query="do something",
                intent=ConversationalIntent.ACTION,
                components=[]
            ),
            components=[]
        )
    )

def test_decision_response_valid():
    dr = DecisionResponse(status=DecisionStatus.PROCEED)
    assert dr.status == DecisionStatus.PROCEED
    assert dr.confirmation_context is None
    assert len(dr.recommendations) == 0

def test_confirmation_required_valid():
    req = create_mock_request()
    nonce = str(uuid.uuid4())
    cr = ConfirmationRequired(
        nonce=nonce,
        original_request=req,
        structured_data={"key": "value"}
    )
    
    dr = DecisionResponse(
        status=DecisionStatus.CONFIRMATION_REQUIRED,
        confirmation_context=cr
    )
    assert dr.confirmation_context.nonce == nonce
    assert dr.confirmation_context.structured_data["key"] == "value"

def test_recommendation_valid():
    req = create_mock_request()
    rec = Recommendation(
        proposed_request=req,
        structured_data={"suggestion": "reorder"}
    )
    dr = DecisionResponse(
        status=DecisionStatus.PROCEED,
        recommendations=[rec]
    )
    assert dr.recommendations[0].structured_data["suggestion"] == "reorder"

def test_confirmation_intent():
    assert ConversationalIntent.CONFIRMATION.value == "CONFIRMATION"

def test_rejection_intent():
    assert ConversationalIntent.REJECTION.value == "REJECTION"

def test_invalid_decision_status():
    with pytest.raises(ValidationError):
        DecisionResponse(status="INVALID")

def test_missing_request_in_confirmation():
    with pytest.raises(ValidationError):
        ConfirmationRequired(nonce="123")
