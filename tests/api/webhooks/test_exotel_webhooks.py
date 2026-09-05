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

# 1. VoiceBot Session Start: metadata.call_sid + custom_parameters.CustomField
@pytest.mark.asyncio
async def test_session_start_voicebot_nested(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": {"CustomField": "eng-123|req-123"}
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200
    assert response.json()["response"]["data"]["session constants"]["engagement_id"] == "eng-123"
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.CONNECTED
    assert doc["provider_session_id"] == "voicebot-call-1"

# 2. raw/string custom_parameters
@pytest.mark.asyncio
async def test_session_start_raw_custom_parameters(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": "eng-123|req-123"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200
    
# 3. external_id fallback
@pytest.mark.asyncio
async def test_session_start_external_id(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "external_id": "eng-123|req-123"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200

# 4. root CustomField backward compatibility
@pytest.mark.asyncio
async def test_session_start_root_customfield(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "CallSid": "call-old",
        "CustomField": "eng-123|req-123"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["provider_session_id"] == "call-old"

# 5. Transcript with metadata.call_sid and no CustomField
@pytest.mark.asyncio
async def test_transcript_metadata_call_sid(repo, mock_db):
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", provider_session_id="voicebot-call-1",
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "EventId": "evt-123",
        "transcript": "Hello"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.IN_PROGRESS

# 6. Pre-Agent with metadata.call_sid
@pytest.mark.asyncio
async def test_pre_agent_metadata_call_sid(repo, mock_db):
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", provider_session_id="voicebot-call-1",
        status=EngagementState.IN_PROGRESS
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "EventId": "evt-pre-agent"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/pre-agent-transfer", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.ESCALATED

# 7. Session End with metadata.call_sid
@pytest.mark.asyncio
async def test_session_end_metadata_call_sid(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", provider_session_id="voicebot-call-1",
        status=EngagementState.IN_PROGRESS
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "EventId": "evt-end",
        "Status": "completed"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-end", json=payload, headers=get_headers())
    assert response.status_code == 200
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.COMPLETED

# 8. out-of-order event before Session Start
@pytest.mark.asyncio
async def test_out_of_order_transcript(repo, mock_db):
    await repo.setup_indexes()
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "EventId": "evt-123",
        "transcript": "Hello out of order"
    }
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    event = await mock_db.customer_engagement_events.find_one({"provider_event_id": "evt-123"})
    assert event["engagement_id"] is None
    assert event["provider_session_id"] == "voicebot-call-1"

# 9. orphan retroactive resolution
@pytest.mark.asyncio
async def test_orphan_resolution(repo, mock_db):
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL"
    )
    await repo.create_engagement(record)
    
    await mock_db.customer_engagement_events.insert_one({
        "provider_session_id": "voicebot-call-1",
        "engagement_id": None,
        "event_type": "transcript"
    })
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": "eng-123|req-123"
    }
    client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    
    event = await mock_db.customer_engagement_events.find_one({"provider_session_id": "voicebot-call-1"})
    assert event["engagement_id"] == "eng-123"

# 10. duplicate callback idempotency
@pytest.mark.asyncio
async def test_duplicate_callback_idempotency(repo, mock_db):
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", provider_session_id="voicebot-call-1",
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "EventId": "evt-dup",
        "transcript": "Hello"
    }
    
    res1 = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    res2 = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": "eng-123", "provider_event_id": "evt-dup"})
    assert events == 1

# 11. invalid Bearer rejection
@pytest.mark.asyncio
async def test_invalid_bearer_rejection(repo, mock_db):
    payload = {"CallSid": "call-1"}
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers={"Authorization": "Bearer badtoken"})
    assert response.status_code == 401

# 12. valid Bearer acceptance
# Validated implicitly by other passing tests

# 13. authentication failure causes no DB mutation
@pytest.mark.asyncio
async def test_no_db_mutation_on_auth_failure(repo, mock_db):
    payload = {"CallSid": "call-1", "CustomField": "eng-123|req-123"}
    client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers={"Authorization": "Bearer badtoken"})
    
    docs = await mock_db.customer_engagements.count_documents({})
    assert docs == 0

# 14. conflicting correlation candidates are rejected
@pytest.mark.asyncio
async def test_conflicting_correlation_rejected(repo, mock_db):
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": "eng-123|req-123",
        "external_id": "eng-999|req-999"
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 400
    assert "Ambiguous" in response.json()["detail"]

# 15. conflicting CallSid sources are rejected
@pytest.mark.asyncio
async def test_conflicting_callsid_rejected(repo, mock_db):
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "CallSid": "call-different",
        "custom_parameters": "eng-123|req-123"
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 400
    assert "Ambiguous" in response.json()["detail"]

# 16. malformed correlation candidate is rejected
@pytest.mark.asyncio
async def test_malformed_correlation_rejected(repo, mock_db):
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": "just-a-string-without-pipe"
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 400
    assert "Missing" in response.json()["detail"]

# 17. multiple identical correlation candidates are accepted once
@pytest.mark.asyncio
async def test_identical_correlation_accepted(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": "eng-123|req-123",
        "external_id": "eng-123|req-123"
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200

# 18. late evidence after terminal state remains monotonic
@pytest.mark.asyncio
async def test_late_evidence_monotonic(repo, mock_db):
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel=OutreachChannel.VOICE, provider="EXOTEL", provider_session_id="voicebot-call-1",
        status=EngagementState.COMPLETED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "EventId": "evt-late",
        "transcript": "Late transcript"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.COMPLETED
