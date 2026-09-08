"""
Outbound Writeback Worker — delivers committed NDR intelligence results to ShopDeck BS.

Architectural role:
  Exotel session-end webhook
  → claim_intelligence_writeback (CAS, one-per-engagement)
  → enqueue_intelligence_writeback (MongoDB outbox, idempotent)
  → HTTP 200 returned immediately

  This worker (separate from ndr_queue_poller):
  → claim_pending_writeback (atomic findOneAndUpdate, lease-fenced)
  → shopdeck_cem.submit_intelligence
  → DELIVERED  /  retry (PENDING + backoff)  /  DEAD_LETTER

Retry policy:
  MAX_DELIVERY_ATTEMPTS: transient failures retry up to this count, then DEAD_LETTER.
  Exponential backoff: 2^attempt_count minutes, capped at 60 min.
  Retry-After header on 429 is respected if it exceeds the exponential delay.

Shutdown:
  stop() sets _running=False and cancels the internal asyncio Task.
  process_next() is always awaited to completion inside the task loop before checking
  _running, so a claim that is in-flight when stop() is called will complete its
  state transition before the task exits.
"""
import asyncio
import logging
import uuid
from datetime import datetime, UTC, timedelta
from typing import Optional

import httpx

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository

logger = logging.getLogger(__name__)

# Maximum total delivery attempts (initial + retries) before a record is dead-lettered.
# At exponential backoff the sequence is: 1m, 2m, 4m, 8m, 16m, 32m, 60m (capped).
# 8 attempts gives ~2.5 hours of retry window before permanent failure.
MAX_DELIVERY_ATTEMPTS = 8


class OutboundWritebackWorker:
    """
    Dedicated background daemon that drains the outbound_writeback_queue collection.
    Must be instantiated and started exactly once inside the application lifespan.
    """

    def __init__(
        self,
        repo: CustomerEngagementRepository,
        shopdeck_cem,  # ShopdeckCemAdapter, injected to avoid circular import
        poll_interval: float = 5.0,
    ):
        self.repo = repo
        self.shopdeck_cem = shopdeck_cem
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the worker. Call exactly once inside the application lifespan."""
        if self._task is not None and not self._task.done():
            logger.warning("OutboundWritebackWorker.start() called while already running — ignoring.")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="outbound_writeback_worker")
        logger.info("OutboundWritebackWorker started (poll_interval=%.1fs, max_attempts=%d)",
                    self.poll_interval, MAX_DELIVERY_ATTEMPTS)

    async def stop(self) -> None:
        """
        Signal the worker to stop and await clean shutdown.
        Any in-flight process_next() that has already claimed a record will finish
        its state transition before the task exits — the task loop checks _running
        only in the sleep/wait phase, not mid-claim.
        """
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("OutboundWritebackWorker stopped.")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.process_next()
            except Exception as e:
                logger.error("OutboundWritebackWorker: unhandled exception in process_next: %s: %s",
                             type(e).__name__, e, exc_info=True)
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    async def process_next(self) -> None:
        claim_token = uuid.uuid4().hex
        record = await self.repo.claim_pending_writeback(claim_token=claim_token, lease_seconds=300)
        if not record:
            return

        result_id = record["result_id"]
        engagement_id = record.get("engagement_id", "unknown")
        payload = record["payload"]
        attempt_count = record.get("attempt_count", 0)

        logger.info(
            "Writeback claimed: result_id=%s engagement_id=%s attempt=%d",
            result_id, engagement_id, attempt_count + 1,
        )

        try:
            await self.shopdeck_cem.submit_intelligence(payload)
            await self.repo.mark_writeback_success(result_id, claim_token)
            logger.info(
                "Writeback DELIVERED: result_id=%s engagement_id=%s",
                result_id, engagement_id,
            )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            # Log structured diagnostic info without dumping full customer payload.
            error_msg = f"HTTP {status_code}"
            logger.warning(
                "Writeback HTTP error: result_id=%s engagement_id=%s status=%d",
                result_id, engagement_id, status_code,
            )

            if status_code == 409:
                # persist_intelligence_atomic (business_systems/shopdeck/.../ndr_queue.py)
                # raises two distinct ValueErrors that both surface as 409:
                #   - "engagement_already_has_result": a prior delivery already recorded a
                #     result for this engagement. If it was THIS same result_id, the retry is
                #     an expected idempotent duplicate - the outcome is already stored, so
                #     DELIVERED is correct. A different engagement_id having a result at all
                #     is exactly what this string names, so no further check is needed there.
                #   - "conflicting_result: field '...' differs": the same result_id was
                #     already submitted with DIFFERENT immutable data - a genuine data
                #     integrity problem, not a duplicate. This must dead-letter for
                #     investigation, never be marked DELIVERED, since doing so would silently
                #     hide the conflict. The previous `or status_code == 409` here made this
                #     condition a tautology (always true, since we are already inside the
                #     status_code == 409 branch) and marked every 409 DELIVERED regardless of
                #     which of these two cases it was - masking real conflicts.
                try:
                    body = e.response.json()
                    error_detail = body.get("detail", "") or body.get("error", "")
                except Exception:
                    error_detail = e.response.text or ""
                if "engagement_already_has_result" in error_detail:
                    logger.info(
                        "Writeback 409 idempotent duplicate: result_id=%s engagement_id=%s — marking DELIVERED.",
                        result_id, engagement_id,
                    )
                    await self.repo.mark_writeback_success(result_id, claim_token)
                else:
                    logger.error(
                        "Writeback 409 conflicting_result — dead-lettering: result_id=%s "
                        "engagement_id=%s detail=%s",
                        result_id, engagement_id, error_detail,
                    )
                    await self.repo.mark_writeback_dead_letter(result_id, claim_token, error_msg)

            elif status_code in (401, 403):
                logger.error(
                    "Writeback auth failure %d — dead-lettering: result_id=%s engagement_id=%s",
                    status_code, result_id, engagement_id,
                )
                await self.repo.mark_writeback_dead_letter(result_id, claim_token, error_msg)

            elif 400 <= status_code < 500 and status_code != 429:
                logger.error(
                    "Writeback terminal client error %d — dead-lettering: result_id=%s engagement_id=%s",
                    status_code, result_id, engagement_id,
                )
                await self.repo.mark_writeback_dead_letter(result_id, claim_token, error_msg)

            else:
                # 5xx or 429 — transient
                await self._handle_transient(
                    result_id, claim_token, engagement_id, attempt_count, error_msg,
                    response=e.response,
                )

        except httpx.RequestError as e:
            error_msg = f"Network error: {type(e).__name__}: {e}"
            logger.warning(
                "Writeback network error: result_id=%s engagement_id=%s error=%s",
                result_id, engagement_id, error_msg,
            )
            await self._handle_transient(result_id, claim_token, engagement_id, attempt_count, error_msg)

        except Exception as e:
            error_msg = f"Unexpected: {type(e).__name__}: {e}"
            logger.error(
                "Writeback unexpected error: result_id=%s engagement_id=%s error=%s",
                result_id, engagement_id, error_msg, exc_info=True,
            )
            await self._handle_transient(result_id, claim_token, engagement_id, attempt_count, error_msg)

    async def _handle_transient(
        self,
        result_id: str,
        claim_token: str,
        engagement_id: str,
        attempt_count: int,
        error_msg: str,
        response=None,
    ) -> None:
        new_attempt_count = attempt_count + 1

        if new_attempt_count >= MAX_DELIVERY_ATTEMPTS:
            logger.error(
                "Writeback retry limit reached (%d/%d) — dead-lettering: result_id=%s engagement_id=%s last_error=%s",
                new_attempt_count, MAX_DELIVERY_ATTEMPTS, result_id, engagement_id, error_msg,
            )
            await self.repo.mark_writeback_dead_letter(result_id, claim_token, error_msg)
            return

        # Exponential backoff: 2^attempt_count minutes, capped at 60 min.
        backoff_minutes = min(2 ** attempt_count, 60)

        # Honour Retry-After on 429 if it exceeds the exponential delay.
        if response is not None and response.status_code == 429:
            retry_after_header = response.headers.get("Retry-After", "")
            if retry_after_header.isdigit():
                retry_after_minutes = int(retry_after_header) / 60.0
                if retry_after_minutes > backoff_minutes:
                    backoff_minutes = retry_after_minutes
                    logger.info(
                        "Retry-After header overrides backoff for result_id=%s: %.1f min",
                        result_id, backoff_minutes,
                    )

        next_attempt_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
        await self.repo.mark_writeback_transient_retry(result_id, claim_token, error_msg, next_attempt_at)
        logger.info(
            "Writeback retry scheduled: result_id=%s engagement_id=%s attempt=%d/%d "
            "next_attempt_at=%s backoff=%.1fmin",
            result_id, engagement_id, new_attempt_count, MAX_DELIVERY_ATTEMPTS,
            next_attempt_at.isoformat(), backoff_minutes,
        )
