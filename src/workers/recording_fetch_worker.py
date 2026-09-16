"""
Recording Fetch Worker - background retry pipeline for Sarvam call recordings.

Architectural role:
  Sarvam call-completed webhook
  → enqueue_recording_fetch (MongoDB outbox, idempotent per engagement_id)
  → HTTP 200 returned immediately, no blocking I/O in the webhook handler

  This worker (separate from ndr_queue_poller and outbound_writeback_worker):
  → claim_pending_recording_fetch (atomic findOneAndUpdate, lease-fenced)
  → fetch_and_store_recording (Sarvam analytics API -> R2)
  → shopdeck_cem.update_queue_status(status="call_completed", recording_url=...)
  → DELIVERED  /  retry (PENDING + backoff)  /  DEAD_LETTER

Why this exists (found 2026-09-16): fetching the recording synchronously inside the
call-completed webhook handler failed for every real call that day with a 404 from
Sarvam's analytics/recordings endpoint - the recording isn't processed and available on
Sarvam's side the instant the completion webhook fires. Retrying later (confirmed
manually, minutes after the same 404) succeeds. A queue item's first attempt is
deliberately delayed (see enqueue_recording_fetch's initial_delay_seconds) rather than
tried immediately, since an immediate first attempt would just reproduce the same 404.

Reporting recording_url after the queue has already advanced past call_dispatched:
ShopDeck's PATCH .../queue/{id}/status handler (routers/ndr_queue.py) writes
ndr_engagements.recording_url unconditionally whenever status == "call_completed" is
sent, via its own connection, BEFORE it validates the status transition itself - so a
late report that gets a 409 "Invalid transition" back has still durably written
recording_url; the 409 only means the *queue_status* field itself didn't move (correctly
so, since some other event already advanced it further). This worker treats that specific
409 as success for recording-reporting purposes, not a reason to retry. This depends on
ShopDeck's current (loose) ordering of those two operations - if they later wrap both in
one transaction, a late report would need a genuinely different endpoint instead.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.recording_storage import fetch_and_store_recording

logger = logging.getLogger(__name__)

# Backoff sequence (minutes): 1, 2, 4, 8, 16, 32, 60, 60 - roughly 2 hours of retry window,
# generous because the failure mode observed is "not processed yet on Sarvam's side", which
# resolves itself, not a permanent condition worth giving up on quickly.
MAX_FETCH_ATTEMPTS = 8


class RecordingFetchWorker:
    """
    Dedicated background daemon that drains the recording_fetch_queue collection.
    Must be instantiated and started exactly once inside the application lifespan.
    """

    def __init__(
        self,
        repo: CustomerEngagementRepository,
        shopdeck_cem,  # ShopdeckCemAdapter, injected to avoid circular import
        poll_interval: float = 15.0,
    ):
        self.repo = repo
        self.shopdeck_cem = shopdeck_cem
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            logger.warning("RecordingFetchWorker.start() called while already running — ignoring.")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="recording_fetch_worker")
        logger.info("RecordingFetchWorker started (poll_interval=%.1fs, max_attempts=%d)",
                    self.poll_interval, MAX_FETCH_ATTEMPTS)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("RecordingFetchWorker stopped.")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.process_next()
            except Exception as e:
                logger.error("RecordingFetchWorker: unhandled exception in process_next: %s: %s",
                             type(e).__name__, e, exc_info=True)
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    async def process_next(self) -> None:
        claim_token = uuid.uuid4().hex
        record = await self.repo.claim_pending_recording_fetch(claim_token=claim_token, lease_seconds=300)
        if not record:
            return

        engagement_id = record["engagement_id"]
        interaction_id = record["interaction_id"]
        awb_no = record["awb_no"]
        queue_item_id = record["queue_item_id"]
        attempt_count = record.get("attempt_count", 0)

        logger.info(
            "Recording fetch claimed: engagement_id=%s awb_no=%s attempt=%d",
            engagement_id, awb_no, attempt_count + 1,
        )

        recording_url = await fetch_and_store_recording(interaction_id, awb_no=awb_no, engagement_id=engagement_id)
        if not recording_url:
            await self._handle_transient(
                engagement_id, claim_token, attempt_count,
                "fetch_and_store_recording returned None (not yet available or fetch/upload error)",
            )
            return

        try:
            await self.shopdeck_cem.update_queue_status(
                queue_item_id=queue_item_id,
                status="call_completed",
                engagement_id=engagement_id,
                recording_url=recording_url,
            )
            await self.repo.mark_recording_fetch_success(engagement_id, claim_token)
            logger.info("Recording reported to ShopDeck: engagement_id=%s url=%s", engagement_id, recording_url)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # See module docstring: ShopDeck writes recording_url before validating the
                # status transition, so a 409 here still means the write landed - the queue's
                # own status simply (correctly) didn't move backward/sideways.
                await self.repo.mark_recording_fetch_success(engagement_id, claim_token)
                logger.info(
                    "Recording reported to ShopDeck (queue already past call_dispatched, "
                    "409 on status transition but recording_url still written): engagement_id=%s url=%s",
                    engagement_id, recording_url,
                )
            else:
                await self._handle_transient(
                    engagement_id, claim_token, attempt_count,
                    f"update_queue_status HTTP {e.response.status_code}",
                )

        except Exception as e:
            await self._handle_transient(
                engagement_id, claim_token, attempt_count,
                f"update_queue_status unexpected error: {type(e).__name__}: {e}",
            )

    async def _handle_transient(self, engagement_id: str, claim_token: str, attempt_count: int, error_msg: str) -> None:
        new_attempt_count = attempt_count + 1

        if new_attempt_count >= MAX_FETCH_ATTEMPTS:
            logger.error(
                "Recording fetch retry limit reached (%d/%d) — dead-lettering: engagement_id=%s last_error=%s",
                new_attempt_count, MAX_FETCH_ATTEMPTS, engagement_id, error_msg,
            )
            await self.repo.mark_recording_fetch_dead_letter(engagement_id, claim_token, error_msg)
            return

        backoff_minutes = min(2 ** attempt_count, 60)
        next_attempt_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
        await self.repo.mark_recording_fetch_transient_retry(engagement_id, claim_token, error_msg, next_attempt_at)
        logger.info(
            "Recording fetch retry scheduled: engagement_id=%s attempt=%d/%d next_attempt_at=%s backoff=%.1fmin error=%s",
            engagement_id, new_attempt_count, MAX_FETCH_ATTEMPTS,
            next_attempt_at.isoformat(), backoff_minutes, error_msg,
        )
