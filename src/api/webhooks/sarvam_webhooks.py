from fastapi import APIRouter, Request, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Any, Dict, Optional
import hmac
import logging

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementEvent, EngagementState
from src.shared.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer-engagement/voice/sarvam", tags=["sarvam-webhooks"])

security = HTTPBearer(auto_error=False)


def verify_sarvam_bearer(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> None:
    """
    Verifies SARVAM_WEBHOOK_SECRET.

    PRIMARY mechanism is a `?secret=` query parameter, not a header - confirmed against
    Sarvam's real Instant Outbound docs that webhook_config only supports {url, metadata},
    no auth field of any kind. There is no header for Sarvam to send this in even if it
    wanted to, so SarvamVoiceBotAdapter embeds the secret directly in the URL it gives
    Sarvam (`.../call-completed?secret=...`), the same query-token pattern already proven
    working for Exotel (verify_exotel_bearer). Header checks are kept as a harmless fallback
    only, in case a future Sarvam platform update adds header-based signing.
    """
    expected_token = settings.sarvam_webhook_secret
    if not expected_token:
        raise HTTPException(status_code=500, detail="Server webhook secret unconfigured")

    query_token = request.query_params.get("secret")
    if query_token and hmac.compare_digest(expected_token.encode("utf-8"), query_token.strip().encode("utf-8")):
        return

    if credentials and credentials.credentials:
        if hmac.compare_digest(expected_token.encode("utf-8"), credentials.credentials.encode("utf-8")):
            return

    auth_header = request.headers.get("authorization", "")
    if auth_header:
        raw_token = auth_header.replace("Bearer ", "").replace("bearer ", "").strip()
        if hmac.compare_digest(expected_token.encode("utf-8"), raw_token.encode("utf-8")):
            return

    raise HTTPException(status_code=403, detail="Invalid webhook signature")


def get_repository():
    return CustomerEngagementRepository()


@router.post("/call-completed", dependencies=[Depends(verify_sarvam_bearer)])
async def handle_call_completed(
    request: Request,
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    """
    Real endpoint for Instant Outbound's completion webhook (webhook_config.url, set by
    SarvamVoiceBotAdapter.dispatch_call()). This is the ONLY webhook Instant Outbound sends
    per call - no separate on-start hook or mid-call tool call. engagement_id round-trips
    via webhook_config.metadata, echoed back verbatim by Sarvam - no Exotel-style
    correlation-resolution needed.

    The agent's own LLM decides the outcome directly via a custom on-end tool (not raw
    transcript classification like Exotel) - the decided fields arrive inside
    final_agent_variables: call_summary, call_outcome (one of: rescheduled,
    customer_declined, address_updated, phone_no_update, escalation_requested,
    no_resolution), reattempt_date_selected, address_change_requested ("yes"/"no"),
    new_address_details, phone_no_change_requested ("yes"/"no"), new_phone_number.
    Confirmed directly against the user's real tool configuration (2026-09-12), not
    guessed from platform docs.
    """
    from src.intelligence_domains.ndr.reply_parser import (
        map_sarvam_call_outcome,
        enqueue_ndr_intelligence_result,
    )

    payload = await request.json()

    engagement_id = (payload.get("webhook_config") or {}).get("metadata", {}).get("engagement_id")
    if not engagement_id:
        raise HTTPException(status_code=400, detail="engagement_id not found in webhook_config.metadata")

    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="SARVAM",
        provider_session_id=payload.get("attempt_id"),
        event_type="call-completed",
        provider_event_id=payload.get("interaction_id"),
        payload=payload,
    )
    await repo.log_event(event)

    engagement = await repo.get_engagement(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    status = payload.get("status", "")
    final_state = EngagementState.FAILED if status in ("no_answer", "busy", "failed") else EngagementState.COMPLETED
    await repo.transition_state(engagement_id, final_state)

    final_agent_variables = payload.get("final_agent_variables") or {}
    call_outcome = final_agent_variables.get("call_outcome")
    if not call_outcome:
        logger.info(
            "No call_outcome in final_agent_variables for engagement %s (status=%s) - "
            "nothing to write back (call likely never connected).",
            engagement_id, status,
        )
        return {"status": "received", "written_back": False}

    call_context = engagement.get("call_context", {}) or {}
    queue_item_id = call_context.get("queue_item_id")
    awb_no = engagement.get("awb_no")

    if not queue_item_id or not awb_no or awb_no == "UNKNOWN":
        logger.error(
            "Cannot record NDR outcome for engagement %s: unresolved queue_item_id=%r awb_no=%r",
            engagement_id, queue_item_id, awb_no,
        )
        return {"status": "received", "written_back": False}

    recommended_action, customer_intent, diagnosis = map_sarvam_call_outcome(call_outcome)

    # address_change_requested/phone_no_change_requested are checked independently of
    # call_outcome, not as alternatives to it - a single call can both agree to a
    # reattempt date AND provide a new address, and both facts must land in ShopDeck
    # together rather than one crowding out the other (by user decision, 2026-09-12).
    action_parameters: Dict[str, Any] = {}
    reattempt_date_selected = final_agent_variables.get("reattempt_date_selected")
    if reattempt_date_selected:
        action_parameters["reschedule_date"] = reattempt_date_selected
    if final_agent_variables.get("address_change_requested") == "yes":
        new_address_details = final_agent_variables.get("new_address_details")
        if new_address_details:
            action_parameters["new_address_details"] = new_address_details
    if final_agent_variables.get("phone_no_change_requested") == "yes":
        new_phone_number = final_agent_variables.get("new_phone_number")
        if new_phone_number:
            action_parameters["new_phone_number"] = new_phone_number

    call_summary = final_agent_variables.get("call_summary") or ""
    reasoning = f"Sarvam agent reported call_outcome: {call_outcome}."
    if call_summary:
        reasoning += f" Call summary: {call_summary}"
    failure_reason = payload.get("failure_reason") or ""
    if failure_reason:
        reasoning += f" Sarvam-reported call failure_reason: {failure_reason}"

    await enqueue_ndr_intelligence_result(
        repo,
        engagement_id=engagement_id,
        queue_item_id=queue_item_id,
        awb_no=awb_no,
        recommended_action=recommended_action,
        customer_intent=customer_intent,
        diagnosis=diagnosis,
        reasoning=reasoning,
        provenance="brain.ndr.sarvam_agent_decision",
        action_parameters=action_parameters,
    )

    return {"status": "received", "written_back": True}
