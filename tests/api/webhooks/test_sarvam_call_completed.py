"""
Direct, real-execution coverage for handle_call_completed - the actual live endpoint
SarvamVoiceBotAdapter points Sarvam's completion webhook at. Runs through FastAPI's real
TestClient (not a unit call to internal helpers), with a repository double, to catch what
mocked-at-the-function-level tests would miss - route wiring, auth dependency, response
shape, and the real interaction between final_agent_variables extraction and the
enqueue_ndr_intelligence_result call.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.webhooks.sarvam_webhooks import get_repository
from src.shared.config import settings


def _client_with_mock_repo(engagement: dict) -> tuple[TestClient, AsyncMock]:
    mock_repo = AsyncMock()
    mock_repo.get_engagement.return_value = engagement
    mock_repo.claim_intelligence_writeback.return_value = True
    mock_repo.enqueue_intelligence_writeback.return_value = True
    app.dependency_overrides[get_repository] = lambda: mock_repo
    return TestClient(app), mock_repo


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
    client, mock_repo = _client_with_mock_repo(_base_engagement())
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
    client, mock_repo = _client_with_mock_repo(_base_engagement())
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


def test_address_updated_alone_maps_to_reschedule_not_no_action():
    """
    The core mapping decision (2026-09-12): even with no date confirmed, an address-only
    update still needs a real delivery attempt, so it must not be tagged no_action.
    """
    client, mock_repo = _client_with_mock_repo(_base_engagement())
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
    client, mock_repo = _client_with_mock_repo(_base_engagement())
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
    client, mock_repo = _client_with_mock_repo(_base_engagement())
    response = _post(client, {
        "attempt_id": "attempt_5",
        "status": "no_answer",
        "webhook_config": {"metadata": {"engagement_id": "eng_1", "action_request_id": "act_1"}},
    })
    assert response.status_code == 200
    assert response.json()["written_back"] is False
    mock_repo.enqueue_intelligence_writeback.assert_not_called()


def test_missing_engagement_id_in_metadata_is_rejected():
    client, _ = _client_with_mock_repo(_base_engagement())
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
