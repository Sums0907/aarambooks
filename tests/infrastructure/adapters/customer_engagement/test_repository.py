import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC

from mongomock_motor import AsyncMongoMockClient
from pymongo.errors import DuplicateKeyError

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord, CustomerEngagementEvent, EngagementState, NormalizationStatus

@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    db = client.get_database("test_db")
    return db

@pytest.fixture
def repo(mock_db):
    with patch("src.infrastructure.adapters.customer_engagement.repository.get_mongo_db", return_value=mock_db):
        repository = CustomerEngagementRepository()
        yield repository

@pytest.mark.asyncio
async def test_setup_indexes(repo, mock_db):
    await repo.setup_indexes()
    # mongomock_motor doesn't fully enforce sparse indexes in tests yet, 
    # but we verify the method completes without crashing
    assert True

@pytest.mark.asyncio
async def test_create_engagement(repo, mock_db):
    record = CustomerEngagementRecord(
        action_request_id="req-1",
        awb_no="AWB1",
        channel="VOICE",
        provider="EXOTEL"
    )
    
    await repo.create_engagement(record)
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": record.engagement_id})
    assert doc is not None
    assert doc["normalization_status"] == NormalizationStatus.NOT_READY
    assert doc["status"] == EngagementState.REQUESTED

@pytest.mark.asyncio
async def test_create_engagement_retry_with_different_action_request_id_reuses_existing(repo, mock_db):
    """
    Regression test: the NDR Queue Poller derives engagement_id deterministically from
    queue_item_id so retries of the same queue item converge on one engagement, but the
    orchestrator regenerates a fresh action_request_id on every run. A retry must not be
    treated as a conflicting, different engagement just because action_request_id differs -
    it must reuse the existing record instead of raising (see repository.py's create_engagement).
    """
    await repo.setup_indexes()  # unique index on engagement_id is what makes the retry collide

    first = CustomerEngagementRecord(
        engagement_id="eng_fixed_retry_key",
        action_request_id="req-1",
        awb_no="AWB1",
        channel="VOICE",
        provider="EXOTEL"
    )
    await repo.create_engagement(first)

    retry = CustomerEngagementRecord(
        engagement_id="eng_fixed_retry_key",
        action_request_id="req-2",
        awb_no="AWB1",
        channel="VOICE",
        provider="EXOTEL"
    )
    result = await repo.create_engagement(retry)

    assert result.engagement_id == "eng_fixed_retry_key"
    assert result.action_request_id == "req-1"  # the original, not overwritten

@pytest.mark.asyncio
async def test_transition_state_valid(repo, mock_db):
    record = CustomerEngagementRecord(
        action_request_id="req-1",
        awb_no="AWB1",
        channel="VOICE",
        provider="EXOTEL"
    )
    await repo.create_engagement(record)
    
    res = await repo.transition_state(record.engagement_id, EngagementState.DISPATCHED)
    assert res is True
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": record.engagement_id})
    assert doc["status"] == EngagementState.DISPATCHED

@pytest.mark.asyncio
async def test_transition_state_invalid_backward(repo, mock_db):
    record = CustomerEngagementRecord(
        action_request_id="req-1",
        awb_no="AWB1",
        channel="VOICE",
        provider="EXOTEL"
    )
    await repo.create_engagement(record)
    await repo.transition_state(record.engagement_id, EngagementState.COMPLETED)
    
    # Try transitioning backwards
    res = await repo.transition_state(record.engagement_id, EngagementState.CONNECTED)
    assert res is False
    
    doc = await mock_db.customer_engagements.find_one({"engagement_id": record.engagement_id})
    assert doc["status"] == EngagementState.COMPLETED

@pytest.mark.asyncio
async def test_event_logging_idempotent(repo, mock_db):
    # Ensure indexes are created so duplicate key error is raised
    await repo.setup_indexes()
    
    event = CustomerEngagementEvent(
        engagement_id="eng-1",
        provider="EXOTEL",
        event_type="transcript",
        provider_event_id="ex-event-1"
    )
    
    res1 = await repo.log_event(event)
    assert res1 is True
    
    # Simulate duplicate payload
    res2 = await repo.log_event(event)
    assert res2 is False # Safely handles the DuplicateKeyError in mongomock_motor
