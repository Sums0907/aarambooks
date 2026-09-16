"""
Coverage for RecordingFetchWorker - the background retry pipeline that replaced fetching
call recordings inline inside the Sarvam call-completed webhook (see
tests/api/webhooks/test_sarvam_call_completed.py for why: inline fetch 404'd on every real
call on 2026-09-16 because Sarvam's analytics/recordings endpoint isn't ready the instant
the completion webhook fires).
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.workers.recording_fetch_worker import RecordingFetchWorker, MAX_FETCH_ATTEMPTS


def _queue_record(**overrides) -> dict:
    record = {
        "engagement_id": "eng_1",
        "interaction_id": "20260916/abcd-10:00:00-efgh",
        "awb_no": "AWB123",
        "queue_item_id": "q_1",
        "attempt_count": 0,
        "status": "PROCESSING",
        "claim_token": "token123",
    }
    record.update(overrides)
    return record


@pytest.mark.asyncio
async def test_successful_fetch_reports_recording_and_marks_delivered():
    repo = AsyncMock()
    repo.claim_pending_recording_fetch.return_value = _queue_record()
    shopdeck_cem = AsyncMock()
    worker = RecordingFetchWorker(repo=repo, shopdeck_cem=shopdeck_cem)

    with patch(
        "src.workers.recording_fetch_worker.fetch_and_store_recording",
        new=AsyncMock(return_value="https://recordings.aarambooks.cloud/sarvam_call_recordings/AWB123/eng_1.wav"),
    ):
        await worker.process_next()

    shopdeck_cem.update_queue_status.assert_awaited_once_with(
        queue_item_id="q_1",
        status="call_completed",
        engagement_id="eng_1",
        recording_url="https://recordings.aarambooks.cloud/sarvam_call_recordings/AWB123/eng_1.wav",
    )
    # The worker mints its own claim_token per process_next() call (same pattern as
    # OutboundWritebackWorker) - assert it's whatever token was used to claim, not a literal.
    claimed_token = repo.claim_pending_recording_fetch.call_args.kwargs["claim_token"]
    repo.mark_recording_fetch_success.assert_awaited_once_with("eng_1", claimed_token)
    repo.mark_recording_fetch_transient_retry.assert_not_called()


@pytest.mark.asyncio
async def test_still_404_schedules_retry_not_dead_letter_on_first_attempt():
    """
    The exact real-world failure mode: recording not yet available on Sarvam's side.
    Must be treated as transient and retried, not given up on immediately.
    """
    repo = AsyncMock()
    repo.claim_pending_recording_fetch.return_value = _queue_record(attempt_count=0)
    shopdeck_cem = AsyncMock()
    worker = RecordingFetchWorker(repo=repo, shopdeck_cem=shopdeck_cem)

    with patch(
        "src.workers.recording_fetch_worker.fetch_and_store_recording",
        new=AsyncMock(return_value=None),
    ):
        await worker.process_next()

    shopdeck_cem.update_queue_status.assert_not_called()
    repo.mark_recording_fetch_dead_letter.assert_not_called()
    repo.mark_recording_fetch_transient_retry.assert_awaited_once()
    claimed_token = repo.claim_pending_recording_fetch.call_args.kwargs["claim_token"]
    args = repo.mark_recording_fetch_transient_retry.call_args[0]
    assert args[0] == "eng_1"
    assert args[1] == claimed_token


@pytest.mark.asyncio
async def test_late_409_on_status_transition_still_counts_as_success():
    """
    ShopDeck's PATCH .../status handler writes ndr_engagements.recording_url unconditionally
    whenever status="call_completed" is sent, BEFORE it validates the queue_status
    transition itself (confirmed directly against ShopDeck's route source, 2026-09-16). So a
    409 "Invalid transition" here means the recording_url write already landed - only the
    queue_status field itself (correctly) didn't move, because some other event (e.g. the
    outcome writeback) already advanced it past call_dispatched. This must be treated as
    success, not retried.
    """
    repo = AsyncMock()
    repo.claim_pending_recording_fetch.return_value = _queue_record()
    shopdeck_cem = AsyncMock()
    conflict_response = httpx.Response(
        status_code=409, request=httpx.Request("PATCH", "https://api-shopdeck.aarambooks.cloud/x"),
        json={"detail": "Invalid transition: action_ready → call_completed. Allowed from: ['call_dispatched']"},
    )
    shopdeck_cem.update_queue_status.side_effect = httpx.HTTPStatusError(
        "409", request=conflict_response.request, response=conflict_response
    )
    worker = RecordingFetchWorker(repo=repo, shopdeck_cem=shopdeck_cem)

    with patch(
        "src.workers.recording_fetch_worker.fetch_and_store_recording",
        new=AsyncMock(return_value="https://recordings.aarambooks.cloud/sarvam_call_recordings/AWB123/eng_1.wav"),
    ):
        await worker.process_next()

    claimed_token = repo.claim_pending_recording_fetch.call_args.kwargs["claim_token"]
    repo.mark_recording_fetch_success.assert_awaited_once_with("eng_1", claimed_token)
    repo.mark_recording_fetch_transient_retry.assert_not_called()
    repo.mark_recording_fetch_dead_letter.assert_not_called()


@pytest.mark.asyncio
async def test_exhausting_retries_dead_letters_instead_of_retrying_forever():
    repo = AsyncMock()
    repo.claim_pending_recording_fetch.return_value = _queue_record(attempt_count=MAX_FETCH_ATTEMPTS - 1)
    shopdeck_cem = AsyncMock()
    worker = RecordingFetchWorker(repo=repo, shopdeck_cem=shopdeck_cem)

    with patch(
        "src.workers.recording_fetch_worker.fetch_and_store_recording",
        new=AsyncMock(return_value=None),
    ):
        await worker.process_next()

    repo.mark_recording_fetch_dead_letter.assert_awaited_once()
    repo.mark_recording_fetch_transient_retry.assert_not_called()


@pytest.mark.asyncio
async def test_no_pending_record_is_a_quiet_no_op():
    repo = AsyncMock()
    repo.claim_pending_recording_fetch.return_value = None
    shopdeck_cem = AsyncMock()
    worker = RecordingFetchWorker(repo=repo, shopdeck_cem=shopdeck_cem)

    await worker.process_next()

    shopdeck_cem.update_queue_status.assert_not_called()
