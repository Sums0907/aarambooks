"""
Regression coverage for the NDR context-richness work: pincode (for the same-pincode
address-change rule), prior communication history (calls/SMS/WhatsApp), and the real
two-date reattempt window (confirmed directly against ShopDeck's own NDR console, which
always offers exactly today+1 and today+2, regardless of attempt number).

These tests build a real CCC through ccc_builder.build()/project() against a mocked
evidence provider shaped exactly like ShopDeck's real NDRShipmentContext JSON response
(not a hand-built CustomerConversationProjection), then verify the fields survive all the
way into build_session_constants()'s output - the same two-ended pattern
test_ndr_mission_contracts.py already uses for the mission fields, applied to this new data.
"""
import sys
from unittest.mock import AsyncMock, MagicMock
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['pymongo.errors'] = MagicMock()

import re
from datetime import datetime, timedelta

import pytest

from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ConversationalDirective
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus


SHOPDECK_EVIDENCE = {
    "customer_name": "Rahul",
    "customer.attribute.phone": "9999999999",
    "cod_amount": 499.0,
    "payment_mode": "cod",
    "courier_partner": "Delhivery",
    "ndr_count": 2,
    "drop_pincode": "122001",
    "items": [{"sku_id": "SKU1", "product_name": "Cotton Bedsheet", "quantity": 1, "selling_price": 499.0}],
    "action_history": [
        {"action_type": "whatsapp_hsm", "action_by": "SYSTEM", "response_status": "no_response", "message_text": None, "is_priority_escalate": False},
        {"action_type": "ivr_call", "action_by": "AI_AGENT", "response_status": "customer_unavailable", "message_text": None, "is_priority_escalate": False},
    ],
}


def _mock_provider(evidence: dict) -> AsyncMock:
    provider = AsyncMock()
    provider.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data=evidence,
    )
    return provider


def _action_request() -> ActionRequest:
    directive = ConversationalDirective(objective="x", context_summary="y", allowed_actions=[], constraints=[])
    return ActionRequest(
        action_request_id="a1",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="test",
        parameters={"awb_no": "AWB123"},
        directive=directive,
    )


@pytest.mark.asyncio
async def test_destination_pincode_reaches_the_projection():
    builder = CustomerConversationContextBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE))
    ccc = await builder.build(_action_request())
    assert ccc.order_facts.destination_pincode == "122001"
    projection = builder.project(ccc)
    assert projection.destination_pincode == "122001"


@pytest.mark.asyncio
async def test_prior_communication_summary_reflects_real_history_not_invented():
    builder = CustomerConversationContextBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert "whatsapp_hsm" in projection.prior_communication_summary
    assert "no_response" in projection.prior_communication_summary
    assert "ivr_call" in projection.prior_communication_summary
    assert "customer_unavailable" in projection.prior_communication_summary


@pytest.mark.asyncio
async def test_no_prior_history_is_stated_plainly_not_omitted_or_invented():
    evidence = dict(SHOPDECK_EVIDENCE)
    evidence["action_history"] = []
    builder = CustomerConversationContextBuilder(provider=_mock_provider(evidence))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.prior_communication_summary == "No prior outreach recorded for this order."


@pytest.mark.asyncio
async def test_offered_reattempt_dates_are_exactly_tomorrow_and_day_after():
    builder = CustomerConversationContextBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    expected_1 = (datetime.now() + timedelta(days=1)).strftime("%A (%d-%m-%Y)")
    expected_2 = (datetime.now() + timedelta(days=2)).strftime("%A (%d-%m-%Y)")
    assert projection.offered_reattempt_date_1 == expected_1
    assert projection.offered_reattempt_date_2 == expected_2


@pytest.mark.asyncio
async def test_reschedule_window_is_read_from_ndr_config_not_hardcoded():
    """
    3rd attempt is configured as a 0-day window (src/intelligence_domains/ndr/config.py) -
    no dates should be offered at all, even though this test builds a CCC directly (the
    orchestrator's own policy would normally prevent a 3rd-attempt call from dispatching at
    all - this proves the window computation itself also respects the same policy value,
    rather than only relying on the orchestrator to prevent the call).
    """
    evidence = dict(SHOPDECK_EVIDENCE)
    evidence["ndr_count"] = 3
    builder = CustomerConversationContextBuilder(provider=_mock_provider(evidence))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.offered_reattempt_date_1 is None
    assert projection.offered_reattempt_date_2 is None


@pytest.mark.asyncio
async def test_diagnostic_priority_instruction_absent_on_first_attempt():
    evidence = dict(SHOPDECK_EVIDENCE)
    evidence["ndr_count"] = 1
    builder = CustomerConversationContextBuilder(provider=_mock_provider(evidence))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.diagnostic_priority_instruction is None


@pytest.mark.asyncio
async def test_diagnostic_priority_instruction_present_from_second_attempt():
    builder = CustomerConversationContextBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE))  # ndr_count=2
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.diagnostic_priority_instruction is not None
    assert "why the earlier delivery attempt" in projection.diagnostic_priority_instruction


def test_new_fields_and_instructions_reach_session_constants():
    from src.api.webhooks.exotel_webhooks import build_session_constants

    call_context = {
        "destination_pincode": "122001",
        "prior_communication_summary": "whatsapp_hsm -> no_response",
        "offered_reattempt_date_1": "Wednesday (09-09-2026)",
        "offered_reattempt_date_2": "Thursday (10-09-2026)",
        "past_delivery_attempts": 2,
        "courier_partner": "Delhivery",  # deliberately must NOT reach session_constants
    }
    sc = build_session_constants(
        engagement_id="eng_1", action_request_id="act_1",
        engagement={"call_context": call_context},
    )
    assert sc["destination_pincode"] == "122001"
    assert sc["prior_communication_summary"] == "whatsapp_hsm -> no_response"
    assert sc["offered_reattempt_date_1"] == "Wednesday (09-09-2026)"
    assert sc["offered_reattempt_date_2"] == "Thursday (10-09-2026)"
    assert sc["past_delivery_attempts"] == "2"
    assert "courier_partner" not in sc, "courier_partner must stay withheld per the no-leakage rule"
    assert "instruction_pincode_lock" in sc
    assert "instruction_reattempt_dates" in sc
    assert "instruction_prior_communication" in sc
