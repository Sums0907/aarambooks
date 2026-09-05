import pytest
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
    repository = CustomerEngagementRepository()
    repository._db = mock_db
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    app.dependency_overrides = {}

def get_headers():
    return {"Authorization": f"Bearer {settings.aaram_exotel_webhook_secret}"}

@pytest.mark.asyncio
async def test_session_start_webhook_success(repo, mock_db):
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
        "CustomField": "eng-123|req-123"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    
    assert response.status_code == 200
    data = response.json()
    assert data["response"]["data"]["session constants"]["engagement_id"] == "eng-123"
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.CONNECTED
    assert doc["provider_session_id"] == "call-1"

@pytest.mark.asyncio
async def test_webhook_invalid_bearer(repo, mock_db):
    payload = {"CallSid": "call-1"}
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers={"Authorization": "Bearer badtoken"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_missing_bearer(repo, mock_db):
    payload = {"CallSid": "call-1"}
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload)
    assert response.status_code == 403 # FastAPI HTTPBearer returns 403 when missing

@pytest.mark.asyncio
async def test_transcript_out_of_order(repo, mock_db):
    await repo.setup_indexes()
    
    payload = {
        "CallSid": "call-1",
        "EventId": "evt-123",
        "transcript": "Hello"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    # Event should be logged with engagement_id=None
    event = await mock_db.customer_engagement_events.find_one({"provider_event_id": "evt-123"})
    assert event is not None
    assert event["engagement_id"] is None
    assert event["provider_session_id"] == "call-1"

@pytest.mark.asyncio
async def test_session_start_resolves_orphans(repo, mock_db):
    await repo.setup_indexes()
    
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL"
    )
    await repo.create_engagement(record)
    
    # Orphan event exists
    await mock_db.customer_engagement_events.insert_one({
        "provider_session_id": "call-1",
        "engagement_id": None,
        "event_type": "transcript"
    })
    
    payload = {
        "CallSid": "call-1",
        "CustomField": "eng-123|req-123"
    }
    client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    
    # Event should now be linked
    event = await mock_db.customer_engagement_events.find_one({"provider_session_id": "call-1"})
    assert event["engagement_id"] == "eng-123"

@pytest.mark.asyncio
async def test_transcript_resolves_via_callsid(repo, mock_db):
    await repo.setup_indexes()
    
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        provider_session_id="call-1",
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CallSid": "call-1",
        "EventId": "evt-123",
        "transcript": "Hello"
    }
    
    # No CustomField in payload!
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.IN_PROGRESS

@pytest.mark.asyncio
async def test_transcript_after_completed_does_not_regress(repo, mock_db):
    await repo.setup_indexes()
    
    record = CustomerEngagementRecord(
        engagement_id="eng-123",
        action_request_id="req-123",
        awb_no="AWB123",
        channel=OutreachChannel.VOICE,
        provider="EXOTEL",
        provider_session_id="call-1",
        status=EngagementState.COMPLETED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CallSid": "call-1",
        "EventId": "evt-late",
        "transcript": "Late transcript"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.COMPLETED
    
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
        provider_session_id="call-1",
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CallSid": "call-1",
        "EventId": "evt-dup",
        "transcript": "Hello"
    }
    
    res1 = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    res2 = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    
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
        provider_session_id="call-1",
        status=EngagementState.IN_PROGRESS
    )
    await repo.create_engagement(record)
    
    payload = {
        "CallSid": "call-1",
        "EventId": "evt-end",
        "Status": "completed"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-end", json=payload, headers=get_headers())
    
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.COMPLETED
    assert doc["normalization_status"] == "PENDING"
