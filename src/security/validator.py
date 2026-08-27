import json
from typing import Dict, Any

MAX_PAYLOAD_SIZE = 256 * 1024  # 256KB

class SecurityValidationError(Exception):
    pass

class PayloadValidator:
    @staticmethod
    def validate_inbound_event(raw_payload: str) -> Dict[str, Any]:
        """Validates raw string payload and returns a safe dictionary."""
        
        if not isinstance(raw_payload, str):
            raise SecurityValidationError("Payload must be a string.")
            
        # 1. Size Limit
        if len(raw_payload) > MAX_PAYLOAD_SIZE:
            raise SecurityValidationError("Payload exceeds maximum allowed size.")
            
        # 2. JSON Structure Validation
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            raise SecurityValidationError("Payload is not valid JSON.")
            
        if not isinstance(parsed, dict):
            raise SecurityValidationError("Payload must be a JSON object.")
            
        # 3. Event Type Validation
        event_type = parsed.get("event_type")
        if not event_type or not isinstance(event_type, str):
            raise SecurityValidationError("Payload missing required string field 'event_type'.")
            
        allowed_events = {"ndr_update", "customer_query"}
        if event_type not in allowed_events:
            raise SecurityValidationError(f"Unsupported event type: {event_type}")
            
        # 4. Content Field Validation
        content = parsed.get("content")
        if content is None or not isinstance(content, dict):
            raise SecurityValidationError("Payload missing required object field 'content'.")
            
        return parsed
