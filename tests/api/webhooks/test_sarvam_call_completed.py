"""
Direct, real-execution coverage for handle_call_completed - the actual live endpoint
SarvamVoiceBotAdapter points Sarvam's completion webhook at. Runs through FastAPI's real
TestClient (not a unit call to internal helpers), with a repository double, to catch what
mocked-at-the-function-level tests would miss - route wiring, auth dependency, response
shape, and the real interaction between final_agent_variables extraction and the
enqueue_ndr_intelligence_result call.
"""
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.webhooks.sarvam_webhooks import get_repository, get_shopdeck_adapter
from src.shared.config import settings


def _client_with_mock_repo(engagement: dict) -> tuple[TestClient, AsyncMock, AsyncMock]:
    mock_repo = AsyncMock()
    mock_repo.get_engagement.return_value = engagement
    mock_repo.claim_intelligence_writeback.return_value = True
    mock_repo.enqueue_intelligence_writeback.return_value = True
    mock_repo.enqueue_recording_fetch.return_value = True
    app.dependency_overrides[get_repository] = lambda: mock_repo

    mock_shopdeck_adapter = AsyncMock()
    app.dependency_overrides[get_shopdeck_adapter] = lambda: mock_shopdeck_adapter

    return TestClient(app), mock_repo, mock_shopdeck_adapter


def _base_engagement() -> dict:
    return {
        "engagement_id": "eng_1",
        "action_request_id": "act_1",
        "awb_no": "AWB123",
        "call_context": {
            "queue_item_id": "q_1",
            "offered_reattempt_date_1": "Friday (12-09-2026)",
            "offered_reattempt_date_2": "Saturday (13-09-2026)",
        },
    }


def _post(client: TestClient, payload: dict):
    return client.post(
        f"/api/customer-engagement/voice/sarvam/call-completed?secret={settings.sarvam_webhook_secret}",
        json=payload,
    )


def teardown_function():
    app.dependency_overrides.clear()


def test_rescheduled_outcome_writes_back_reschedule_with_the_selected_date():
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_1",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer agreed to Friday delivery.",
            "call_outcome": "rescheduled",
            "reattempt_date_selected": "Friday (12-09-2026)",
            "address_change_requested": "no",
            "phone_no_change_requested": "no",
        },
    })
    assert response.status_code == 200
    assert response.json()["written_back"] is True
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["recommended_action"] == "reschedule"
    assert payload["customer_intent"] == "agreed"
    assert payload["action_parameters"]["reschedule_date"] == "Friday (12-09-2026)"


def test_rescheduled_and_address_change_both_land_in_action_parameters_together():
    """
    Regression test for the exact scenario this design decision (2026-09-12) exists for:
    a customer can both agree to a reattempt date AND give a new address in the same call -
    both facts must survive into ShopDeck, not just one of them.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_2",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer agreed to Friday delivery at a corrected address.",
            "call_outcome": "rescheduled",
            "reattempt_date_selected": "Friday (12-09-2026)",
            "address_change_requested": "yes",
            "new_address_details": "Flat 4B, MG Road, Bengaluru, 560001",
            "phone_no_change_requested": "no",
        },
    })
    assert response.status_code == 200
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["recommended_action"] == "reschedule"
    assert payload["action_parameters"]["reschedule_date"] == "Friday (12-09-2026)"
    assert payload["action_parameters"]["new_address_details"] == "Flat 4B, MG Road, Bengaluru, 560001"


def test_new_phone_number_lands_in_action_parameters_when_flag_is_a_real_boolean():
    """
    Regression test for a real production bug found 2026-09-15: every real Sarvam payload
    sends address_change_requested/phone_no_change_requested as a genuine JSON boolean
    (Python True/False after parsing), not the string "yes"/"no" the agent-config docs
    describe and the other tests in this file use. The original `== "yes"` check silently
    dropped new_phone_number/new_address_details on every single real call - confirmed by
    checking a real production result row where the customer gave a new phone number that
    Sarvam correctly captured, but which never reached ndr_intelligence_results.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_3",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer agreed to Friday delivery with an updated phone number.",
            "call_outcome": "rescheduled",
            "reattempt_date_selected": "Friday (12-09-2026)",
            "address_change_requested": False,
            "phone_no_change_requested": True,
            "new_phone_number": "7988373566",
        },
    })
    assert response.status_code == 200
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["action_parameters"]["new_phone_number"] == "7988373566"
    assert "new_address_details" not in payload["action_parameters"]


def test_address_updated_alone_maps_to_reschedule_not_no_action():
    """
    The core mapping decision (2026-09-12): even with no date confirmed, an address-only
    update still needs a real delivery attempt, so it must not be tagged no_action.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_3",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer only wanted to correct the address.",
            "call_outcome": "address_updated",
            "reattempt_date_selected": "",
            "address_change_requested": "yes",
            "new_address_details": "New building, same pincode",
            "phone_no_change_requested": "no",
        },
    })
    assert response.status_code == 200
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["recommended_action"] == "reschedule"
    assert payload["customer_intent"] == "agreed"
    assert payload["action_parameters"]["new_address_details"] == "New building, same pincode"
    assert "reschedule_date" not in payload["action_parameters"]


def test_customer_declined_maps_to_accept_rto():
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_4",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer does not want the order anymore.",
            "call_outcome": "customer_declined",
            "reattempt_date_selected": "",
            "address_change_requested": "no",
            "phone_no_change_requested": "no",
        },
    })
    assert response.status_code == 200
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["recommended_action"] == "accept_rto"
    assert payload["customer_intent"] == "declined"


def test_no_answer_call_with_no_final_agent_variables_writes_back_nothing():
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_5",
        "status": "no_answer",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
    })
    assert response.status_code == 200
    assert response.json()["written_back"] is False
    mock_repo.enqueue_intelligence_writeback.assert_not_called()


def test_recording_fetch_enqueued_for_background_processing_not_fetched_inline():
    """
    Regression test for a real production bug found 2026-09-16: fetching the recording
    synchronously inside this webhook 404'd for every real call that day, because Sarvam's
    analytics/recordings endpoint isn't ready to serve the recording the instant the
    completion webhook fires. The fix is to enqueue the fetch for RecordingFetchWorker to
    retry with backoff, not attempt it inline here - this webhook must never call Sarvam's
    recordings API directly (unlike the call_completed status report below, which is a
    single fast PATCH with no external dependency and is safe to send inline).

    Must fire even when Sarvam produced no decisive call_outcome, since the recording is
    still real, useful evidence regardless - by user decision (2026-09-16), a recording
    isn't something to act on, so it belongs on ndr_engagements.recording_url, not folded
    into ndr_intelligence_results.action_parameters (reserved for things a human must act on).
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_7",
        "status": "connected",
        "interaction_id": "20260916/abcd-10:00:00-efgh",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {},
    })

    assert response.status_code == 200
    mock_repo.enqueue_recording_fetch.assert_awaited_once_with(
        engagement_id="eng_1",
        interaction_id="20260916/abcd-10:00:00-efgh",
        awb_no="AWB123",
        queue_item_id="q_1",
        call_outcome="connected",
        transcript_summary=None,
    )
    # No call_outcome was present, so the existing outcome-writeback path correctly does
    # nothing - the recording enqueue above must not depend on it or leak into it.
    mock_repo.enqueue_intelligence_writeback.assert_not_called()


def test_call_completed_reported_unconditionally_even_with_no_decisive_outcome():
    """
    Regression test for a real production bug found 2026-09-16: 3 real calls that connected
    but produced no decisive call_outcome (customer hung up immediately, empty transcript)
    were left permanently stuck at ShopDeck's queue_status=call_dispatched, because nothing
    in this handler had ever reported them as finished - the only status-advancing call that
    existed was the recording-report side effect, which only fires when a recording
    successfully attaches. ShopDeck's own schema expects call_completed with a raw telephony
    call_outcome (answered/no_answer/failed/cancelled) reported for every call that ends,
    independent of whether Sarvam's agent produced a decisive NDR recommendation.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_9",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {},
    })

    assert response.status_code == 200
    mock_shopdeck_adapter.update_queue_status.assert_awaited_once_with(
        queue_item_id="q_1",
        status="call_completed",
        engagement_id="eng_1",
        call_outcome="connected",
        transcript_summary=None,
    )
    # No call_outcome was present, so the existing outcome-writeback path correctly does
    # nothing - the unconditional status report above must not depend on it.
    mock_repo.enqueue_intelligence_writeback.assert_not_called()


def test_call_completed_report_still_fires_alongside_a_decisive_outcome():
    """
    The unconditional report and the existing outcome-writeback are independent, not
    alternatives - a call that DOES produce a decisive call_outcome must still get both:
    the raw call_completed status report AND the ndr_intelligence_results writeback.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_10",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer agreed to Friday delivery.",
            "call_outcome": "rescheduled",
            "reattempt_date_selected": "Friday (12-09-2026)",
        },
    })

    assert response.status_code == 200
    mock_shopdeck_adapter.update_queue_status.assert_awaited_once_with(
        queue_item_id="q_1",
        status="call_completed",
        engagement_id="eng_1",
        call_outcome="connected",
        transcript_summary="Customer agreed to Friday delivery.",
    )
    mock_repo.enqueue_intelligence_writeback.assert_awaited_once()


def test_call_completed_report_409_does_not_block_outcome_writeback():
    """
    A 409 on the status report (e.g. a duplicate webhook delivery, or the queue already
    moved on) must not raise or block the rest of the handler - the outcome writeback below
    is independent and must still proceed.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    conflict_response = httpx.Response(
        status_code=409, request=httpx.Request("PATCH", "https://api-shopdeck.aarambooks.cloud/x"),
    )
    mock_shopdeck_adapter.update_queue_status.side_effect = httpx.HTTPStatusError(
        "409", request=conflict_response.request, response=conflict_response
    )

    response = _post(client, {
        "attempt_id": "attempt_11",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer agreed to Friday delivery.",
            "call_outcome": "rescheduled",
            "reattempt_date_selected": "Friday (12-09-2026)",
        },
    })

    assert response.status_code == 200
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["recommended_action"] == "reschedule"


def test_recording_not_enqueued_without_interaction_id():
    """
    A call that never produced an interaction_id (e.g. dispatch itself failed before Sarvam
    ever answered) has nothing to fetch a recording for - must not enqueue a doomed retry.
    """
    client, mock_repo, mock_shopdeck_adapter = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_8",
        "status": "connected",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
        "final_agent_variables": {
            "call_summary": "Customer agreed to Friday delivery.",
            "call_outcome": "rescheduled",
            "reattempt_date_selected": "Friday (12-09-2026)",
        },
    })

    assert response.status_code == 200
    mock_repo.enqueue_recording_fetch.assert_not_called()
    payload = mock_repo.enqueue_intelligence_writeback.call_args[0][0]
    assert payload["recommended_action"] == "reschedule"
    assert "recording_url" not in payload["action_parameters"]


def test_missing_engagement_id_in_metadata_is_rejected():
    client, _, _ = _client_with_mock_repo(_base_engagement())
    response = _post(client, {"attempt_id": "attempt_6", "status": "connected", "webhook_config": {"metadata": {}}})
    assert response.status_code == 400


def test_wrong_secret_is_rejected():
    mock_repo = AsyncMock()
    app.dependency_overrides[get_repository] = lambda: mock_repo
    client = TestClient(app)
    response = client.post(
        "/api/customer-engagement/voice/sarvam/call-completed?secret=wrong-secret",
        json={"attempt_id": "x", "status": "connected"},
    )
    assert response.status_code == 403
