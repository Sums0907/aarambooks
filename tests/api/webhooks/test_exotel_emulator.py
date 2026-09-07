import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from src.main import app
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord, EngagementState

from src.api.webhooks.exotel_webhooks import get_repository
from tests.api.webhooks.exotel_emulator import MockExotelEmulator

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

@pytest.fixture
def emulator():
    client = TestClient(app)
    return MockExotelEmulator(client)

async def setup_engagement(repo):
    # Setup initial state
    await repo.setup_indexes()
    eng_id = "eng-emul-1"
    req_id = "req-emul-1"
    record = CustomerEngagementRecord(
        engagement_id=eng_id,
        action_request_id=req_id,
        awb_no="AWB999",
        channel="VOICE",
        provider="EXOTEL",
        status=EngagementState.DISPATCHED
    )
    await repo.create_engagement(record)
    return f"{eng_id}|{req_id}", eng_id

@pytest.mark.asyncio
async def test_scenario_a_customer_unavailable(repo, emulator, mock_db):
    custom_field, eng_id = await setup_engagement(repo)
    
    # 1. Start session
    emulator.emit_session_start(custom_field, "call-scenario-a")
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.CONNECTED
    
    # 2. No transcript. Immediate Session End with "no-answer"
    resp = emulator.emit_session_end(custom_field, "evt-end-a", "no-answer")
    assert resp["status_code"] == 200
    
    # Verify terminal state
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.FAILED
    assert doc["normalization_status"] == "PENDING"
    
    # Verify events
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": eng_id})
    assert events == 1  # Only session-end event logged

@pytest.mark.asyncio
async def test_scenario_b_reschedule_like(repo, emulator, mock_db):
    custom_field, eng_id = await setup_engagement(repo)
    
    emulator.emit_session_start(custom_field, "call-scenario-b")
    emulator.emit_transcript(custom_field, "evt-trans-1", "Hello, I am busy.")
    emulator.emit_transcript(custom_field, "evt-trans-2", "Yes, please deliver tomorrow.")
    emulator.emit_insights(custom_field, "evt-ins-1", {"intent": "reschedule_implied"}) # Raw Exotel NLP observation, not canonical Aaram logic
    
    resp = emulator.emit_session_end(custom_field, "evt-end-b", "completed")
    assert resp["status_code"] == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.COMPLETED
    assert doc["normalization_status"] == "PENDING"
    
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": eng_id})
    assert events == 4 # 2 transcripts, 1 insight, 1 session-end

@pytest.mark.asyncio
async def test_scenario_c_rejected_like(repo, emulator, mock_db):
    custom_field, eng_id = await setup_engagement(repo)
    
    emulator.emit_session_start(custom_field, "call-scenario-c")
    emulator.emit_transcript(custom_field, "evt-trans-3", "I don't want this order, cancel it.")
    
    emulator.emit_session_end(custom_field, "evt-end-c", "completed")
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.COMPLETED
    assert doc["normalization_status"] == "PENDING"

@pytest.mark.asyncio
async def test_scenario_d_duplicate_event_delivery(repo, emulator, mock_db):
    custom_field, eng_id = await setup_engagement(repo)
    
    emulator.emit_session_start(custom_field, "call-scenario-d")
    
    # Send transcript twice
    resp1 = emulator.emit_transcript(custom_field, "evt-dup-trans", "Hello")
    resp2 = emulator.emit_transcript(custom_field, "evt-dup-trans", "Hello")
    
    assert resp1["status_code"] == 200
    assert resp2["status_code"] == 200 # HTTP success for idempotent no-op
    
    # Send session-end twice
    resp3 = emulator.emit_session_end(custom_field, "evt-dup-end", "completed")
    resp4 = emulator.emit_session_end(custom_field, "evt-dup-end", "completed")
    
    assert resp3["status_code"] == 200
    assert resp4["status_code"] == 200
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.COMPLETED
    
    # Only 2 events should actually be persisted
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": eng_id})
    assert events == 2

@pytest.mark.asyncio
async def test_scenario_e_out_of_order_delivery(repo, emulator, mock_db):
    custom_field, eng_id = await setup_engagement(repo)
    
    # Out of order: session-end arrives FIRST
    emulator.emit_session_end(custom_field, "evt-ooo-end", "completed")
    
    # State should jump to COMPLETED
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.COMPLETED
    
    # Late session start arrives
    emulator.emit_session_start(custom_field, "call-scenario-e")
    
    # State should REMAIN COMPLETED (No regression to CONNECTED)
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.COMPLETED
    
    # Late transcript arrives
    emulator.emit_transcript(custom_field, "evt-ooo-trans", "Late transcript")
    
    # State should REMAIN COMPLETED (No regression to IN_PROGRESS)
    doc = await mock_db.customer_engagements.find_one({"engagement_id": eng_id})
    assert doc["status"] == EngagementState.COMPLETED
    assert doc["normalization_status"] == "PENDING"
    
    # Verify both late and early events are stored properly without discarding evidence
    events = await mock_db.customer_engagement_events.count_documents({"engagement_id": eng_id})
    assert events == 2 # session-end and transcript (session-start does not write to events collection currently)
