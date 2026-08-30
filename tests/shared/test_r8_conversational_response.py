import pytest
from pydantic import ValidationError

from src.shared.conversational_contracts import (
    ConversationalResponse,
    ConversationalResponseType,
    ConversationalUnderstanding,
    ConversationalIntent
)

def test_valid_normal_response_construction():
    response = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="Goods Receipt was successfully created.",
        render_directives={"ui_component": "SuccessToast"}
    )
    assert response.response_type == ConversationalResponseType.SUCCESS
    assert response.message == "Goods Receipt was successfully created."
    assert response.render_directives == {"ui_component": "SuccessToast"}

def test_clarification_response_construction():
    response = ConversationalResponse(
        response_type=ConversationalResponseType.CLARIFICATION_REQUIRED,
        message="Please select the correct warehouse.",
        clarification_options=[{"id": "w1", "name": "Main Warehouse"}, {"id": "w2", "name": "Backup Warehouse"}],
        missing_parameters=["warehouse_id"]
    )
    assert response.response_type == ConversationalResponseType.CLARIFICATION_REQUIRED
    assert response.clarification_options[0]["name"] == "Main Warehouse"
    assert "warehouse_id" in response.missing_parameters

def test_serialization_deserialization():
    original = ConversationalResponse(
        response_type=ConversationalResponseType.EXECUTION_LIMITATION,
        message="Insufficient stock.",
        missing_parameters=[]
    )
    dumped = original.model_dump()
    assert dumped["response_type"] == "EXECUTION_LIMITATION"
    assert dumped["message"] == "Insufficient stock."

    reloaded = ConversationalResponse(**dumped)
    assert reloaded.response_type == ConversationalResponseType.EXECUTION_LIMITATION
    assert reloaded.message == "Insufficient stock."

def test_invalid_contract_data_rejected():
    with pytest.raises(ValidationError):
        ConversationalResponse(
            response_type="NOT_A_VALID_TYPE",
            message="This should fail"
        )

def test_backward_compatibility():
    # Proves we haven't broken the existing conversational understanding imports
    cu = ConversationalUnderstanding(
        original_query="Receive 50 units",
        intent=ConversationalIntent.ACTION
    )
    assert cu.intent == ConversationalIntent.ACTION
    assert len(cu.parameters) == 0
