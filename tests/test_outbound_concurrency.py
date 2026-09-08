"""
Concurrency and lease tests for outbound_writeback_queue.

Each test uses _fresh_repo() (new Motor client per test loop).
"""
import asyncio
import uuid
import pymongo
import pytest
from datetime import datetime, UTC, timedelta
from src.infrastructure.mongo_client import MongoDBManager
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository


def _rid():
    return f"test_conc_{uuid.uuid4().hex[:10]}"


async def _fresh_repo() -> CustomerEngagementRepository:
    MongoDBManager.client = None  # Reset singleton so new client binds to this loop
    repo = CustomerEngagementRepository()
    repo._db = None
    db = await repo._get_db()
    await db.outbound_writeback_queue.create_index("result_id", unique=True)
    await db.outbound_writeback_queue.create_index(
        [("status", pymongo.ASCENDING), ("next_attempt_at", pymongo.ASCENDING)]
    )
    await db.outbound_writeback_queue.create_index(
        [("status", pymongo.ASCENDING), ("claimed_at", pymongo.ASCENDING)]
    )
    return repo


async def _cleanup(repo, *result_ids):
    if result_ids:
        db = await repo._get_db()
        await db.outbound_writeback_queue.delete_many({"result_id": {"$in": list(result_ids)}})


async def test_atomic_claim():
    """1 & 2. Atomic Claim & Two-worker Race"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_atomic")
        results = await asyncio.gather(
            repo.claim_pending_writeback(claim_token="token_A", lease_seconds=300),
            repo.claim_pending_writeback(claim_token="token_B", lease_seconds=300),
        )
        successes = [r for r in results if r is not None]
        assert len(successes) == 1
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "PROCESSING"
        assert doc["claim_token"] in ["token_A", "token_B"]
    finally:
        await _cleanup(repo, rid)


async def test_claim_token_fencing():
    """3. Claim Token Fencing"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_fence")
        docA = await repo.claim_pending_writeback(claim_token="token_A", lease_seconds=300)
        assert docA is not None
        # Age the claim to simulate a crashed worker
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"claimed_at": datetime.utcnow() - timedelta(hours=1)}}
        )
        docB = await repo.claim_pending_writeback(claim_token="token_B", lease_seconds=300)
        assert docB is not None and docB["claim_token"] == "token_B"
        assert await repo.mark_writeback_success(rid, "token_A") is False
        assert await repo.mark_writeback_transient_retry(rid, "token_A", "err", datetime.utcnow()) is False
        assert await repo.mark_writeback_success(rid, "token_B") is True
        final_doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert final_doc["status"] == "DELIVERED"
    finally:
        await _cleanup(repo, rid)


async def test_lease_recovery():
    """4. Lease Recovery"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_lease")
        await repo.claim_pending_writeback(claim_token="token_A", lease_seconds=300)
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"claimed_at": datetime.utcnow() - timedelta(hours=1)}}
        )
        doc = await repo.claim_pending_writeback(claim_token="token_B", lease_seconds=300)
        assert doc is not None and doc["claim_token"] == "token_B"
    finally:
        await _cleanup(repo, rid)


async def test_restart_safety():
    """5. Restart Safety"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_restart")
        await repo.claim_pending_writeback(claim_token="token_old", lease_seconds=300)
        db = await repo._get_db()
        await db.outbound_writeback_queue.update_one(
            {"result_id": rid},
            {"$set": {"claimed_at": datetime.utcnow() - timedelta(hours=1)}}
        )
        doc = await repo.claim_pending_writeback(claim_token="token_new", lease_seconds=300)
        assert doc is not None
        await repo.mark_writeback_success(rid, "token_new")
        final = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert final["status"] == "DELIVERED"
    finally:
        await _cleanup(repo, rid)


async def test_idempotency():
    """6. Idempotency"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        r1 = await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_idem")
        r2 = await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_idem")
        assert r1 is True
        assert r2 is False
        db = await repo._get_db()
        count = await db.outbound_writeback_queue.count_documents({"result_id": rid})
        assert count == 1
    finally:
        await _cleanup(repo, rid)


async def test_retry_state():
    """7. Retry State"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_retry")
        await repo.claim_pending_writeback(claim_token="token_retry", lease_seconds=300)
        next_attempt = datetime.utcnow() + timedelta(minutes=5)
        await repo.mark_writeback_transient_retry(rid, "token_retry", "error", next_attempt)
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "PENDING"
        assert doc["attempt_count"] == 1
        claim_again = await repo.claim_pending_writeback(claim_token="token_should_fail", lease_seconds=300)
        assert claim_again is None
    finally:
        await _cleanup(repo, rid)


async def test_dead_letter():
    """8. Dead Letter"""
    repo = await _fresh_repo()
    rid = _rid()
    try:
        await repo.enqueue_intelligence_writeback({"result_id": rid}, "eng_conc_dead")
        await repo.claim_pending_writeback(claim_token="token_dead", lease_seconds=300)
        await repo.mark_writeback_dead_letter(rid, "token_dead", "Auth failed")
        db = await repo._get_db()
        doc = await db.outbound_writeback_queue.find_one({"result_id": rid})
        assert doc["status"] == "DEAD_LETTER"
        claim_again = await repo.claim_pending_writeback(claim_token="token_should_fail", lease_seconds=300)
        assert claim_again is None
    finally:
        await _cleanup(repo, rid)
