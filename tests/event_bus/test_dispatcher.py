import pytest
import json
from src.event_bus.dispatcher import OutboundDispatcher
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory

def test_dispatcher_rejects_non_action_request():
    with pytest.raises(ValueError, match="Dispatcher only accepts ActionRequest objects."):
        OutboundDispatcher.dispatch({"category": "test"})

def test_dispatcher_serializes_action_request():
    action = ActionRequest(
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test reasoning",
        parameters={"test": 123}
    )
    
    output_str = OutboundDispatcher.dispatch(action)
    output = json.loads(output_str)
    
    assert output["event_type"] == "action_dispatched"
    payload = output["payload"]
    assert payload["category"] == ActionCategory.SUGGESTED_RESOLUTION.value
    assert payload["reasoning"] == "Test reasoning"
    assert payload["parameters"]["test"] == 123
