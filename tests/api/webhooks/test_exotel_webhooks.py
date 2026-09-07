import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.main import app
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.api.webhooks.exotel_webhooks import get_repository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord, EngagementState
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
        channel="VOICE", provider="EXOTEL", status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "voicebot-call-1"},
        "custom_parameters": {"CustomField": "eng-123|req-123"}
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200
    assert response.json()["response"]["data"]["session_constants"]["engagement_id"] == "eng-123"
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-123"})
    assert doc["status"] == EngagementState.CONNECTED
    assert doc["provider_session_id"] == "voicebot-call-1"

# 2. raw/string custom_parameters
@pytest.mark.asyncio
async def test_session_start_raw_custom_parameters(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel="VOICE", provider="EXOTEL", status=EngagementState.DISPATCHED
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
        channel="VOICE", provider="EXOTEL", status=EngagementState.DISPATCHED
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
        channel="VOICE", provider="EXOTEL", status=EngagementState.DISPATCHED
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
        channel="VOICE", provider="EXOTEL", provider_session_id="voicebot-call-1",
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
        channel="VOICE", provider="EXOTEL", provider_session_id="voicebot-call-1",
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
        channel="VOICE", provider="EXOTEL", provider_session_id="voicebot-call-1",
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
        channel="VOICE", provider="EXOTEL"
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
        channel="VOICE", provider="EXOTEL", provider_session_id="voicebot-call-1",
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
    assert response.status_code in [400, 404]

# 17. multiple identical correlation candidates are accepted once
@pytest.mark.asyncio
async def test_identical_correlation_accepted(repo, mock_db):
    record = CustomerEngagementRecord(
        engagement_id="eng-123", action_request_id="req-123", awb_no="AWB123",
        channel="VOICE", provider="EXOTEL", status=EngagementState.DISPATCHED
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
        channel="VOICE", provider="EXOTEL", provider_session_id="voicebot-call-1",
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


# ==============================================================================
# CERTIFIED EXOTEL VOICEBOT V2 CONTRACT TESTS
# ==============================================================================

# 19. Session Start with native VoiceBot v2 payload: metadata.call_sid, custom_parameters={}, no CustomField
@pytest.mark.asyncio
async def test_session_start_native_voicebot_v2_call_sid(repo, mock_db):
    """
    Verifies that native Exotel VoiceBot v2 callbacks with metadata.call_sid
    and empty custom_parameters correlate against provider_call_id saved during outbound dispatch.
    """
    record = CustomerEngagementRecord(
        engagement_id="eng-v2-1", 
        action_request_id="act-v2-1", 
        awb_no="AWB-V2-001",
        channel="VOICE", 
        provider="EXOTEL", 
        provider_call_id="call-sid-native-1", # Saved at dispatch time
        status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    
    payload = {
        "session_id": "8fa2b874-972d-45df-b427-df2f2f70eb47",
        "conversation_id": "c138b556-91e7-4977-8ea0-47ec05a5a1f1",
        "metadata": {"call_sid": "call-sid-native-1"},
        "custom_parameters": {},
        "bot_name": "SUNEHRI"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    body = response.json()
    assert body["http_code"] == 200
    data = body["response"]["data"]
    
    # Verify strict snake_case schema and NO spaced keys
    assert "greeting_message" in data
    assert "greeting message" not in data
    assert "session_constants" in data
    assert "session constants" not in data
    assert "webhook_config" in data
    
    # Verify constants
    assert data["session_constants"]["engagement_id"] == "eng-v2-1"
    assert data["session_constants"]["action_request_id"] == "act-v2-1"
    assert data["session_constants"]["brand_name"] == "Aaram Homes"
    assert data["session_constants"]["awb_no"] == "AWB-V2-001"
    
    # Verify webhook endpoints
    assert "/api/customer-engagement/voice/exotel/session-end" in data["webhook_config"]["session_end"]["url"]
    assert "/api/customer-engagement/voice/exotel/transcript" in data["webhook_config"]["transcript_events"]["url"]
    assert "/api/customer-engagement/voice/exotel/pre-agent-transfer" in data["webhook_config"]["pre_agent_transfer"]["url"]
    
    # Verify DB transition
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-v2-1"})
    assert doc["status"] == EngagementState.CONNECTED
    assert doc["provider_session_id"] == "call-sid-native-1"

# 20. Session Start with unknown CallSid fails closed without creating ghost engagements
@pytest.mark.asyncio
async def test_session_start_unknown_call_sid_fails_closed(repo, mock_db):
    """
    Verifies that unknown CallSid fails closed (HTTP 404) and no ghost engagement is created.
    """
    payload = {
        "metadata": {"call_sid": "call-sid-ghost-unknown"},
        "custom_parameters": {}
    }
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    count = await mock_db.customer_engagements.count_documents({})
    assert count == 0

# 21. Transcript with metadata.call_sid resolves via provider_call_id
@pytest.mark.asyncio
async def test_transcript_resolves_via_provider_call_id(repo, mock_db):
    """
    Verifies that transcript callbacks correlate with provider_call_id.
    """
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-v2-2",
        action_request_id="act-v2-2",
        awb_no="AWB-V2-002",
        channel="VOICE",
        provider="EXOTEL",
        provider_call_id="call-sid-native-2", # Saved at dispatch, session_id was null
        status=EngagementState.CONNECTED
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "call-sid-native-2"},
        "EventId": "evt-transcript-v2",
        "events": [{
            "event_type": "transcript",
            "event_id": "evt-transcript-v2",
            "event_data": {
                "transcripts": [{
                    "sequence": 1,
                    "status": "completed",
                    "transcript_segments": [{
                        "speaker": "user",
                        "text": "Kal bhej do subah 10 baje"
                    }]
                }]
            }
        }]
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-v2-2"})
    assert doc["status"] == EngagementState.IN_PROGRESS
    
    event = await mock_db.customer_engagement_events.find_one({"provider_session_id": "call-sid-native-2"})
    assert event["engagement_id"] == "eng-v2-2"

# 22. Session End with metadata.call_sid resolves via provider_call_id and completes lifecycle
@pytest.mark.asyncio
async def test_session_end_resolves_via_provider_call_id(repo, mock_db):
    """
    Verifies that session-end correlates with provider_call_id and transitions to COMPLETED.
    """
    await repo.setup_indexes()
    record = CustomerEngagementRecord(
        engagement_id="eng-v2-3",
        action_request_id="act-v2-3",
        awb_no="AWB-V2-003",
        channel="VOICE",
        provider="EXOTEL",
        provider_call_id="call-sid-native-3",
        status=EngagementState.IN_PROGRESS
    )
    await repo.create_engagement(record)
    
    payload = {
        "metadata": {"call_sid": "call-sid-native-3"},
        "EventId": "evt-end-v2",
        "Status": "completed"
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-end", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": "eng-v2-3"})
    assert doc["status"] == EngagementState.COMPLETED

# 23. Dynamic greeting strictly grounds to Aaram Homes bedsheet catalog without hallucinations
@pytest.mark.asyncio
async def test_dynamic_greeting_grounding_and_no_hallucinations(repo, mock_db):
    """
    Verifies that the generated greeting strictly adheres to Aaram Homes home linen domain
    and does not invent electronics, fake dates, or unconfirmed mutations.
    """
    record = CustomerEngagementRecord(
        engagement_id="eng-v2-4",
        action_request_id="act-v2-4",
        awb_no="AWB-V2-004",
        channel="VOICE",
        provider="EXOTEL",
        provider_call_id="call-sid-native-4",
        status=EngagementState.DISPATCHED
    )
    doc = record.model_dump()
    doc["customer_name"] = "Priya Sharma"
    doc["courier_partner"] = "Delhivery"
    doc["call_context"] = {"product_name": "Premium Cotton Bedsheet"}
    await mock_db.customer_engagements.insert_one(doc)
    
    payload = {
        "metadata": {"call_sid": "call-sid-native-4"},
        "custom_parameters": {}
    }
    
    response = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert response.status_code == 200
    
    greeting = response.json()["response"]["data"]["greeting_message"]["text"].lower()
    assert "aaram homes" in greeting
    assert "bedsheet" in greeting
    
    # Assert zero unauthorized hallucinations
    assert "headphone" not in greeting
    assert "iphone" not in greeting
    assert "phone" not in greeting.lower()
    assert "rescheduled your delivery" not in greeting.lower()

# 23. Exotel Console UI Test URL validation ping
@pytest.mark.asyncio
async def test_exotel_console_test_url_validation_ping(repo, mock_db):
    """
    Verifies that Exotel console Test URL validator pings on all 4 webhook endpoints
    return the exact schema required by Exotel validator (method, request_id, http_code, response.http_code).
    """
    req_id = "6a229fb5-0ade-4762-8276-5cec607d6299"
    payload = {
        "session_id": "<voicebot session id>",
        "external_id": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "bot_name": "bot_name",
        "bot_id": "bot_uuid",
        "metadata": {"call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
        "request_id": req_id
    }
    
    # Session start
    res_start = client.post("/api/customer-engagement/voice/exotel/session-start", json=payload, headers=get_headers())
    assert res_start.status_code == 200
    b_start = res_start.json()
    assert b_start["http_code"] == 200
    assert b_start["method"] == "test_ping_acknowledged"
    assert b_start["request_id"] == req_id
    assert b_start["response"]["http_code"] == 200
    assert b_start["response"]["data"]["webhook_config"]["session_end"]["method"] == "POST"
    assert b_start["response"]["data"]["webhook_config"]["transcript_events"]["method"] == "POST"
    assert b_start["response"]["data"]["webhook_config"]["pre_agent_transfer"]["method"] == "POST"
    
    # Transcript
    res_tx = client.post("/api/customer-engagement/voice/exotel/transcript", json=payload, headers=get_headers())
    assert res_tx.status_code == 200
    b_tx = res_tx.json()
    assert b_tx["http_code"] == 200
    assert b_tx["method"] == "test_ping_acknowledged"
    assert b_tx["response"]["http_code"] == 200
    
    # Session end
    res_end = client.post("/api/customer-engagement/voice/exotel/session-end", json=payload, headers=get_headers())
    assert res_end.status_code == 200
    b_end = res_end.json()
    assert b_end["http_code"] == 200
    assert b_end["method"] == "test_ping_acknowledged"
    assert b_end["response"]["http_code"] == 200
    
    # Pre-agent transfer
    res_pre = client.post("/api/customer-engagement/voice/exotel/pre-agent-transfer", json=payload, headers=get_headers())
    assert res_pre.status_code == 200
    b_pre = res_pre.json()
    assert b_pre["http_code"] == 200
    assert b_pre["method"] == "test_ping_acknowledged"
    assert b_pre["response"]["http_code"] == 200

