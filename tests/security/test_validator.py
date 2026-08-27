import pytest
import json
from src.security.validator import PayloadValidator, SecurityValidationError

def test_validator_rejects_oversized_payload():
    large_payload = "a" * (256 * 1024 + 1)
    with pytest.raises(SecurityValidationError, match="Payload exceeds maximum allowed size."):
        PayloadValidator.validate_inbound_event(large_payload)

def test_validator_rejects_non_string():
    with pytest.raises(SecurityValidationError, match="Payload must be a string."):
        PayloadValidator.validate_inbound_event(123)

def test_validator_rejects_invalid_json():
    with pytest.raises(SecurityValidationError, match="Payload is not valid JSON."):
        PayloadValidator.validate_inbound_event("{not_json}")

def test_validator_rejects_json_array():
    with pytest.raises(SecurityValidationError, match="Payload must be a JSON object."):
        PayloadValidator.validate_inbound_event("[]")

def test_validator_rejects_missing_event_type():
    payload = json.dumps({"content": {}})
    with pytest.raises(SecurityValidationError, match="Payload missing required string field 'event_type'."):
        PayloadValidator.validate_inbound_event(payload)

def test_validator_rejects_unknown_event_type():
    payload = json.dumps({"event_type": "unknown_event", "content": {}})
    with pytest.raises(SecurityValidationError, match="Unsupported event type: unknown_event"):
        PayloadValidator.validate_inbound_event(payload)

def test_validator_rejects_missing_content():
    payload = json.dumps({"event_type": "customer_query"})
    with pytest.raises(SecurityValidationError, match="Payload missing required object field 'content'."):
        PayloadValidator.validate_inbound_event(payload)

def test_validator_accepts_valid_payload():
    payload = json.dumps({"event_type": "customer_query", "content": {"query_text": "hello"}})
    parsed = PayloadValidator.validate_inbound_event(payload)
    assert parsed["event_type"] == "customer_query"
    assert parsed["content"]["query_text"] == "hello"
