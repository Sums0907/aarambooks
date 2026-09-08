"""
Outbound Writeback Queue — integration + unit test matrix.

Each test creates its own CustomerEngagementRepository instance (fresh Motor
client per test loop). This works correctly with pytest-asyncio v1.4.0 which
gives each test its own event loop.

Classification:
  [REAL]   = exercises actual MongoDB (local instance required)
  [MOCKED] = mocks ShopDeck HTTP call only; Mongo operations are real

Test IDs:
  A  enqueue_success
  B  duplicate_result_id
  C  atomic_claim
  D  two_worker_race
  E  claim_token_fencing
  F  lease_recovery
  G  retry_scheduling
  H  retry_limit → DEAD_LETTER
  H2 below_limit → PENDING
  I  dead_letter_not_reclaimed
  J  409_idempotency
  K  retry_after_longer_than_backoff
  K2 retry_after_shorter_than_backoff
  L  webhook_cas_enqueue_success
  M  enqueue_failure_cas_recoverable
  N  duplicate_webhook
  O  worker_startup (MOCKED)
  P  worker_restart_recovery
  Q  payload_preservation
"""
import asyncio
import uuid
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock

import httpx
import motor.motor_asyncio
import pymongo
import pytest

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.workers.outbound_writeback_worker import OutboundWritebackWorker, MAX_DELIVERY_ATTEMPTS

MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "aarambooks_ndr_communications"


import asyncio
import uuid
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock

import httpx
import pymongo
import pytest

from src.infrastructure.mongo_client import MongoDBManager
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.workers.outbound_writeback_worker import OutboundWritebackWorker, MAX_DELIVERY_ATTEMPTS


def _rid() -> str:
    return f"test_owq_{uuid.uuid4().hex[:12]}"


async def _fresh_repo() -> CustomerEngagementRepository:
    """Create a repo with a fresh Motor client bound to the current test loop."""
    # Reset the singleton so the next call creates a new client on the current loop.
    MongoDBManager.client = None
    repo = CustomerEngagementRepository()
    repo._db = None  # force _get_db to re-create
    db = await repo._get_db()
    # Idempotently ensure indexes exist
    await db.outbound_writeback_queue.create_index("result_id", unique=True)
    await db.outbound_writeback_queue.create_index(
        [("status", pymongo.ASCENDING), ("next_attempt_at", pymongo.ASCENDING)]
    )
    await db.outbound_writeback_queue.create_index(
        [("status", pymongo.ASCENDING), ("claimed_at", pymongo.ASCENDING)]
    )
    return repo


async def _cleanup(repo: CustomerEngagementRepository, *result_ids: str):
    if result_ids:
        db = await repo._get_db()
        await db.outbound_writeback_queue.delete_many({"result_id": {"$in": list(result_ids)}})


def _make_worker(repo: CustomerEngagementRepository, mock_cem) -> OutboundWritebackWorker:
    return OutboundWritebackWorker(repo=repo, shopdeck_cem=mock_cem, poll_interval=0.01)


# ---------------------------------------------------------------------------
# A. Enqueue success  [REAL]
# ---------------------------------------------------------------------------
async def test_A_enqueue_success():
    repo = await _fresh_repo()
    rid = _rid()
    try:
        payload = {"result_id": rid, "engagement_id": "eng_A"}
        result = await repo.enqueue_intelligence_writeback(payload, "eng_A")
        assert result is True
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "PENDING"
        assert doc["attempt_count"] == 0
        assert doc["engagement_id"] == "eng_A"
        assert doc["payload"] == payload
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# B. Duplicate result_id  [REAL]
# ---------------------------------------------------------------------------
async def test_B_duplicate_result_id():
    repo = await _fresh_repo()
    rid = _rid()
    try:
        payload = {"result_id": rid}
        r1 = await repo.enqueue_intelligence_writeback(payload, "eng_B")
        r2 = await repo.enqueue_intelligence_writeback(payload, "eng_B")
        assert r1 is True
        assert r2 is False
        db = await repo._get_db()
        count = await db.outbound_writeback_queue.count_documents({"result_id": rid})
        assert count == 1
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# C. Atomic claim  [REAL]
# ---------------------------------------------------------------------------
async def test_C_atomic_claim():
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_C")
        results = await asyncio.gather(
            repo.claim_pending_writeback("tokenC1", lease_seconds=300),
            repo.claim_pending_writeback("tokenC2", lease_seconds=300),
        )
        successes = [r for r in results if r is not None]
        assert len(successes) == 1
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "PROCESSING"
        assert doc["claim_token"] in ("tokenC1", "tokenC2")
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# D. Two-worker race  [REAL]
# ---------------------------------------------------------------------------
async def test_D_two_worker_race():
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_D")
        tokens = [f"token_D_{i}" for i in range(10)]
        results = await asyncio.gather(*[
            repo.claim_pending_writeback(t, lease_seconds=300) for t in tokens
        ])
        assert len([r for r in results if r is not None]) == 1
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# E. Claim token fencing  [REAL]
# ---------------------------------------------------------------------------
async def test_E_claim_token_fencing():
    """[REAL] Stale worker token cannot write; active worker token succeeds."""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_E")
        # Worker A claims, then we force claimed_at to 1 hour ago to simulate expired lease
        await repo.claim_pending_writeback("tokenA_E", lease_seconds=300)
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"claimed_at": datetime.utcnow() - timedelta(hours=1)}}
        )
        # Worker B reclaims the stale lease
        doc_B = await repo.claim_pending_writeback("tokenB_E", lease_seconds=300)
        assert doc_B is not None and doc_B["claim_token"] == "tokenB_E"
        # Worker A's stale token must be rejected
        assert await repo.mark_writeback_success(rid, "tokenA_E") is False
        assert await repo.mark_writeback_transient_retry(rid, "tokenA_E", "err", datetime.utcnow()) is False
        # Worker B succeeds
        assert await repo.mark_writeback_success(rid, "tokenB_E") is True
        final = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert final["status"] == "DELIVERED"
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# F. Lease recovery  [REAL]
# ---------------------------------------------------------------------------
async def test_F_lease_recovery():
    """[REAL] A worker that crashes (expired lease) can be reclaimed by a new worker."""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_F")
        # Old worker claims, then "crashes" — simulate by aging claimed_at to 1 hour ago
        await repo.claim_pending_writeback("tokenF_old", lease_seconds=300)
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"claimed_at": datetime.utcnow() - timedelta(hours=1)}}
        )
        # New worker reclaims successfully
        doc = await repo.claim_pending_writeback("tokenF_new", lease_seconds=300)
        assert doc is not None and doc["claim_token"] == "tokenF_new"
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# G. Retry scheduling  [REAL]
# ---------------------------------------------------------------------------
async def test_G_retry_scheduling():
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_G")
        await repo.claim_pending_writeback("tokenG", lease_seconds=300)
        future = datetime.utcnow() + timedelta(minutes=5)
        ok = await repo.mark_writeback_transient_retry(rid, "tokenG", "timeout", future)
        assert ok is True
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "PENDING"
        assert doc["attempt_count"] == 1
        assert doc["next_attempt_at"] > datetime.utcnow()
        assert await repo.claim_pending_writeback("tokenG_early", lease_seconds=300) is None
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# H. Retry limit → DEAD_LETTER  [REAL + MOCKED]
# ---------------------------------------------------------------------------
async def test_H_retry_limit_dead_letters():
    repo = await _fresh_repo()
    rid = _rid()
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(
        side_effect=httpx.RequestError("timeout", request=httpx.Request("POST", "http://x"))
    )
    worker = _make_worker(repo, mock_cem)
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_H")
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"attempt_count": MAX_DELIVERY_ATTEMPTS - 1}}
        )
        await worker.process_next()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "DEAD_LETTER", f"Expected DEAD_LETTER, got {doc['status']}"
        assert doc["last_error"] is not None
    finally:
        await _cleanup(repo, rid)


async def test_H2_below_retry_limit_stays_pending():
    repo = await _fresh_repo()
    rid = _rid()
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(
        side_effect=httpx.RequestError("timeout", request=httpx.Request("POST", "http://x"))
    )
    worker = _make_worker(repo, mock_cem)
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_H2")
        await worker.process_next()
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "PENDING"
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# I. Dead letter not reclaimed  [REAL]
# ---------------------------------------------------------------------------
async def test_I_dead_letter_not_reclaimed():
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_I")
        await repo.claim_pending_writeback("tokenI", lease_seconds=300)
        await repo.mark_writeback_dead_letter(rid, "tokenI", "auth failure")
        result = await repo.claim_pending_writeback("tokenI_new", lease_seconds=300)
        assert result is None
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# J. 409 idempotency  [REAL + MOCKED]
# ---------------------------------------------------------------------------
async def test_J_409_idempotency():
    repo = await _fresh_repo()
    rid = _rid()
    response_409 = httpx.Response(
        409,
        json={"detail": "engagement_already_has_result"},
        request=httpx.Request("POST", "http://x"),
    )
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(
        side_effect=httpx.HTTPStatusError("409", request=response_409.request, response=response_409)
    )
    worker = _make_worker(repo, mock_cem)
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_J")
        await worker.process_next()
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "DELIVERED"
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# K. Retry-After header  [REAL + MOCKED]
# ---------------------------------------------------------------------------
async def test_K_retry_after_longer_than_backoff():
    """Retry-After=3600s overrides exponential backoff (1 min at attempt 0)."""
    repo = await _fresh_repo()
    rid = _rid()
    response_429 = httpx.Response(
        429,
        headers={"Retry-After": "3600"},
        request=httpx.Request("POST", "http://x"),
    )
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(
        side_effect=httpx.HTTPStatusError("429", request=response_429.request, response=response_429)
    )
    worker = _make_worker(repo, mock_cem)
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_K")
        await worker.process_next()
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        delta = (doc["next_attempt_at"] - datetime.utcnow()).total_seconds()
        assert delta > 59 * 60, f"Expected ~60min delay, got {delta:.0f}s"
    finally:
        await _cleanup(repo, rid)


async def test_K2_retry_after_shorter_than_backoff():
    """Retry-After=5s < 60s exponential → exponential wins."""
    repo = await _fresh_repo()
    rid = _rid()
    response_429 = httpx.Response(
        429,
        headers={"Retry-After": "5"},
        request=httpx.Request("POST", "http://x"),
    )
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(
        side_effect=httpx.HTTPStatusError("429", request=response_429.request, response=response_429)
    )
    worker = _make_worker(repo, mock_cem)
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_K2")
        await worker.process_next()
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        delta = (doc["next_attempt_at"] - datetime.utcnow()).total_seconds()
        assert delta > 50, f"Expected ~60s, got {delta:.0f}s"
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# L. Webhook CAS + enqueue success  [REAL]
# ---------------------------------------------------------------------------
async def test_L_webhook_cas_and_enqueue_success():
    repo = await _fresh_repo()
    rid = _rid()
    engagement_id = f"eng_L_{uuid.uuid4().hex[:8]}"
    try:
        from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord
        from src.intelligence_domains.ndr.contracts.action_request import OutreachChannel
        record = CustomerEngagementRecord(
            engagement_id=engagement_id,
            action_request_id=f"ar_{uuid.uuid4().hex[:8]}",
            awb_no="TEST_AWB_L",
            channel=OutreachChannel.VOICE,
            provider="EXOTEL",
        )
        await repo.create_engagement(record)
        won = await repo.claim_intelligence_writeback(engagement_id, rid)
        assert won is True
        enqueued = await repo.enqueue_intelligence_writeback(
            {"result_id": rid, "engagement_id": engagement_id}, engagement_id
        )
        assert enqueued is True
        db = await repo._get_db()
        count = await db.outbound_writeback_queue.count_documents({"result_id": rid})
        assert count == 1
    finally:
        db = await repo._get_db()
        await db.customer_engagements.delete_one({"engagement_id": engagement_id})
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# M. Enqueue failure → CAS recoverable via duplicate webhook  [REAL]
# ---------------------------------------------------------------------------
async def test_M_enqueue_failure_cas_recoverable():
    repo = await _fresh_repo()
    rid = _rid()
    engagement_id = f"eng_M_{uuid.uuid4().hex[:8]}"
    try:
        from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord
        from src.intelligence_domains.ndr.contracts.action_request import OutreachChannel
        record = CustomerEngagementRecord(
            engagement_id=engagement_id,
            action_request_id=f"ar_{uuid.uuid4().hex[:8]}",
            awb_no="TEST_AWB_M",
            channel=OutreachChannel.VOICE,
            provider="EXOTEL",
        )
        await repo.create_engagement(record)
        # Delivery 1: CAS wins, enqueue "fails" (not called)
        won1 = await repo.claim_intelligence_writeback(engagement_id, rid)
        assert won1 is True
        # Delivery 2: duplicate webhook — CAS returns False, but enqueue runs
        won2 = await repo.claim_intelligence_writeback(engagement_id, rid)
        assert won2 is False
        # Idempotent re-enqueue recovers the outcome
        enqueued = await repo.enqueue_intelligence_writeback({"result_id": rid}, engagement_id)
        assert enqueued is True
        db = await repo._get_db()
        count = await db.outbound_writeback_queue.count_documents({"result_id": rid})
        assert count == 1
    finally:
        db = await repo._get_db()
        await db.customer_engagements.delete_one({"engagement_id": engagement_id})
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# N. Duplicate webhook  [REAL]
# ---------------------------------------------------------------------------
async def test_N_duplicate_webhook():
    repo = await _fresh_repo()
    rid = _rid()
    engagement_id = f"eng_N_{uuid.uuid4().hex[:8]}"
    try:
        from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord
        from src.intelligence_domains.ndr.contracts.action_request import OutreachChannel
        record = CustomerEngagementRecord(
            engagement_id=engagement_id,
            action_request_id=f"ar_{uuid.uuid4().hex[:8]}",
            awb_no="TEST_AWB_N",
            channel=OutreachChannel.VOICE,
            provider="EXOTEL",
        )
        await repo.create_engagement(record)
        payload = {"result_id": rid}
        won1 = await repo.claim_intelligence_writeback(engagement_id, rid)
        assert won1 is True
        r1 = await repo.enqueue_intelligence_writeback(payload, engagement_id)
        assert r1 is True
        won2 = await repo.claim_intelligence_writeback(engagement_id, rid)
        assert won2 is False
        r2 = await repo.enqueue_intelligence_writeback(payload, engagement_id)
        assert r2 is False  # Already exists
        db = await repo._get_db()
        assert await db.outbound_writeback_queue.count_documents({"result_id": rid}) == 1
    finally:
        db = await repo._get_db()
        await db.customer_engagements.delete_one({"engagement_id": engagement_id})
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# O. Worker startup  [MOCKED]
# ---------------------------------------------------------------------------
async def test_O_worker_startup():
    mock_repo = AsyncMock()
    mock_repo.claim_pending_writeback = AsyncMock(return_value=None)
    mock_cem = AsyncMock()
    worker = OutboundWritebackWorker(repo=mock_repo, shopdeck_cem=mock_cem, poll_interval=60)
    try:
        worker.start()
        assert worker._task is not None and not worker._task.done()
        task_before = worker._task
        worker.start()  # Double-start is a no-op
        assert worker._task is task_before
    finally:
        await worker.stop()


# ---------------------------------------------------------------------------
# P. Worker restart recovery  [REAL + MOCKED]
# ---------------------------------------------------------------------------
async def test_P_worker_restart_recovery():
    """[REAL + MOCKED] After worker crash (stale PROCESSING record), new worker reclaims and delivers."""
    repo = await _fresh_repo()
    rid = _rid()
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(return_value={"status": "ok"})
    worker = _make_worker(repo, mock_cem)
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_P")
        # Old worker claims, then "crashes" — age its lease to 1 hour ago
        await repo.claim_pending_writeback("token_old_P", lease_seconds=300)
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"claimed_at": datetime.utcnow() - timedelta(hours=1)}}
        )
        # New worker reclaims and delivers
        await worker.process_next()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "DELIVERED"
    finally:
        await _cleanup(repo, rid)


# ---------------------------------------------------------------------------
# Q. Payload preservation  [REAL + MOCKED]
# ---------------------------------------------------------------------------
async def test_Q_payload_preservation():
    repo = await _fresh_repo()
    rid = _rid()
    captured = []
    mock_cem = AsyncMock()
    mock_cem.submit_intelligence = AsyncMock(
        side_effect=lambda p: captured.append(dict(p)) or {"ok": True}
    )
    worker = _make_worker(repo, mock_cem)
    original_payload = {
        "result_id": rid,
        "engagement_id": "eng_Q",
        "awb_no": "AWB_Q_123",
        "recommended_action": "reattempt",
        "customer_intent": "RESCHEDULE",
    }
    try:
        await repo.enqueue_intelligence_writeback(original_payload, "eng_Q")
        await worker.process_next()
        assert len(captured) == 1
        assert captured[0] == original_payload
    finally:
        await _cleanup(repo, rid)
