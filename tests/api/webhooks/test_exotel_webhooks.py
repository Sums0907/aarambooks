import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.main import app
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.api.webhooks.exotel_webhooks import get_repository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord, EngagementState
from src.intelligence_domains.ndr.contracts.action_request import OutreachChannel
from src.shared.config import settings

client = TestClient(app)

@pytest.fixture
def mock_db():
    mock_client = AsyncMongoMockClient()
    db = mock_client.get_database("test_db")
    return db

@pytest.fixture
def repo(mock_db):
    # Create repository manually bypassing the get_mongo_db call that hits localhost
    repository = CustomerEngagementRepository()
    repository._db = mock_db
    
    # Override FastAPI dependency
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    
    # Clear overrides after test
    app.dependency_overrides = {}

def sign_custom_field(engagement_id: str, action_request_id: str) -> str:
    base = f"{engagement_id}|{action_request_id}"
    sig = hmac.new(
        settings.aaram_exotel_webhook_secret.encode('utf-8'),
        base.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{base}|{sig}"

@pytest.mark.asyncio
async def test_session_start_webhook_success(repo, mock_db):
    # Setup state
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CallSid": "call-1",
        "CustomField": sign_custom_field("eng-123", "req-123")
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"]["data"]["session constants"]["engagement_id"] == "eng-123"
    
    # Verify state transitioned
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.CONNECTED
    assert doc["provider_session_id"] == "call-1"

@pytest.mark.asyncio
async def test_webhook_invalid_signature(repo, mock_db):
    payload = {
        "CallSid": "call-1",
        "CustomField": "eng-123|req-123|forged_signature"
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_missing_signature(repo, mock_db):
    payload = {
        "CallSid": "call-1",
        "CustomField": "eng-123|req-123"
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_transcript_webhook_success(repo, mock_db):
    await repo.setup_indexes()
    
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CustomField": sign_custom_field("eng-123", "req-123"),
        "EventId": "evt-123",
        "transcript": "Hello"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload)
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.IN_PROGRESS
    
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": "eng-123"})
    assert events == 1

@pytest.mark.asyncio
async def test_transcript_after_completed_does_not_regress(repo, mock_db):
    await repo.setup_indexes()
    
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        status=EngagementState.COMPLETED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CustomField": sign_custom_field("eng-123", "req-123"),
        "EventId": "evt-late",
        "transcript": "Late transcript"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload)
    assert response.status_code == 200
    
    # State MUST remain COMPLETED (no regression)
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.COMPLETED
    
    # The late evidence MUST still be logged
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": "eng-123", "event_type": "transcript"})
    assert events == 1

@pytest.mark.asyncio
async def test_duplicate_events_are_idempotent(repo, mock_db):
    await repo.setup_indexes()
    
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CustomField": sign_custom_field("eng-123", "req-123"),
        "EventId": "evt-dup",
        "transcript": "Hello"
    }
    
    res1 = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload)
    res2 = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload)
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    
    # Still only 1 event recorded
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": "eng-123", "event_type": "transcript"})
    assert events == 1

@pytest.mark.asyncio
async def test_session_end_webhook(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        status=EngagementState.IN_PROGRESS
    )
    await repo.create_engagement(record)
    
    payload = {
        "CustomField": sign_custom_field("eng-123", "req-123"),
        "EventId": "evt-end",
        "Status": "completed"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-end", json=payload)
    
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.COMPLETED
    assert doc["normalization_status"] == "PENDING"
