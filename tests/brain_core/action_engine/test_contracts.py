import pytest
from pydantic import ValidationError
from src.brain_core.action_engine.contracts import ActionRequest, ActionResponse, ActionCategory

def test_action_request_valid():
    req = ActionRequest(
        category=ActionCategory.RECOMMENDATION,
        reasoning="Because logic dictates it.",
        parameters={"product_id": "123"}
    )
    assert req.category == ActionCategory.RECOMMENDATION
    assert req.reasoning == "Because logic dictates it."
    assert req.parameters == {"product_id": "123"}

def test_action_request_frozen():
    req = ActionRequest(
        category=ActionCategory.RECOMMENDATION,
        reasoning="Because logic dictates it.",
        parameters={"product_id": "123"}
    )
    with pytest.raises(ValidationError):
        req.reasoning = "New reasoning"

def test_action_request_no_extra_fields():
    with pytest.raises(ValidationError):
        ActionRequest(
            category=ActionCategory.RECOMMENDATION,
            reasoning="Logic.",
            parameters={},
            extra_field="invalid"
        )

def test_action_response_valid():
    resp = ActionResponse(
        success=True,
        message="Action completed",
        execution_result={"status": "done"}
    )
    assert resp.success is True
    assert resp.message == "Action completed"
    assert resp.execution_result == {"status": "done"}

def test_action_response_optional_result():
    resp = ActionResponse(
        success=False,
        message="Failed"
    )
    assert resp.success is False
    assert resp.execution_result is None

def test_action_response_frozen():
    resp = ActionResponse(
        success=True,
        message="Done"
    )
    with pytest.raises(ValidationError):
        resp.success = False
