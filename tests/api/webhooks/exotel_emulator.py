import uuid
import datetime
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient

class MockExotelEmulator:
    """
    Deterministic Exotel Provider Emulator.
    Drives the real FastAPI HTTP Customer Engagement webhook endpoints via TestClient.
    Uses Exotel's exact documented payload schema.
    DOES NOT mutate Aaram business logic or assign canonical outcomes.
    """
    def __init__(self, client: TestClient):
        self.client = client
        
    def _create_payload(self, custom_field: str, event_id: str, **kwargs) -> Dict[str, Any]:
        """Base Exotel Webhook Payload Shape"""
        payload = {
            "CallSid": "mock_call_" + str(uuid.uuid4())[:8],
            "CustomField": custom_field,
            "EventId": event_id,
            "Timestamp": datetime.datetime.now(datetime.UTC).isoformat()
        }
        payload.update(kwargs)
        return payload

    def _get_headers(self):
        from src.shared.config import settings
        return {"Authorization": f"Bearer {settings.aaram_exotel_webhook_secret}"}

    def emit_session_start(self, custom_field: str, call_sid: str) -> dict:
        """
        Emits a session-start event. Note: Exotel session-start doesn't natively have EventId,
        but has CallSid and CustomField.
        """
        payload = {
            "CallSid": call_sid,
            "CustomField": custom_field,
            "Direction": "outbound-api"
        }
        response = self.client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=self._get_headers())
        return {"status_code": response.status_code, "json": response.json()}

    def emit_transcript(self, custom_field: str, event_id: str, transcript: str) -> dict:
        """
        Emits a transcript event.
        """
        payload = self._create_payload(
            custom_field=custom_field, 
            event_id=event_id,
            transcript=transcript
        )
        response = self.client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=self._get_headers())
        return {"status_code": response.status_code, "json": response.json()}
        
    def emit_insights(self, custom_field: str, event_id: str, insights_data: Dict[str, Any]) -> dict:
        """
        Emits an insights event containing structured NLP extraction from Exotel (NOT Brain).
        """
        payload = self._create_payload(
            custom_field=custom_field,
            event_id=event_id,
            insights=insights_data
        )
        response = self.client.post("/api/customer-engagement/voice/exotel/insights", json=payload, headers=self._get_headers())
        return {"status_code": response.status_code, "json": response.json()}

    def emit_session_end(self, custom_field: str, event_id: str, call_status: str) -> dict:
        """
        Emits a session-end event (terminal state).
        call_status usually "completed", "failed", "busy", "no-answer"
        """
        payload = self._create_payload(
            custom_field=custom_field,
            event_id=event_id,
            Status=call_status
        )
        response = self.client.post("/api/customer-engagement/voice/exotel/session-end", json=payload, headers=self._get_headers())
        return {"status_code": response.status_code, "json": response.json()}
