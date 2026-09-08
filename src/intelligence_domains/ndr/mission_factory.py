"""
NDR mission construction.

Ownership boundary (docs/01-architecture/domain-ownership.md):
  - ShopDeck BS owns business truth (why the delivery failed, how many attempts).
  - NDR-ID (this module) owns mission INTERPRETATION: turning that truth into an
    explicit objective, success condition and permitted actions.
  - CCC carries the result into the voice session.
  - Exotel/Priya is execution only, and may not invent facts or mutate business truth.

This is deliberately a pure function over the claimed queue item. It performs no I/O and
must run BEFORE ccc_builder.build(), because the mission is an INPUT to the CCC, not an
output of it. Anything sourced from CCC hydration (e.g. product attributes) is therefore
unavailable here by construction.
"""

from enum import StrEnum
from typing import Any, Dict, Optional

from src.brain_core.action_engine.contracts import ConversationMissionContract

NDR_MISSION = "NDR_RECOVERY"


class NDRConversationState(StrEnum):
    """
    The V1 NDR conversation state vocabulary.

    These nine names are the approved contract. RETURN_TO_NDR in particular is load-bearing:
    it is the state that represents "the side question is answered, now come back to the
    delivery problem" — the single behaviour that separates a goal-directed agent from an
    FAQ bot. Do not collapse it into CONVERSING or drop it.
    """
    INTRODUCE_REASON = "INTRODUCE_REASON"
    CUSTOMER_RESPONSE = "CUSTOMER_RESPONSE"
    ANSWER_CUSTOMER_QUESTION = "ANSWER_CUSTOMER_QUESTION"
    RETURN_TO_NDR = "RETURN_TO_NDR"
    CONFIRM_RESOLUTION = "CONFIRM_RESOLUTION"
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    CUSTOMER_REFUSED = "CUSTOMER_REFUSED"
    UNCLEAR = "UNCLEAR"
    COMPLETED = "COMPLETED"


TERMINAL_STATES = frozenset({
    NDRConversationState.COMPLETED,
    NDRConversationState.CUSTOMER_UNAVAILABLE,
    NDRConversationState.CUSTOMER_REFUSED,
})

# V1 permitted actions. Priya may do these and nothing else. Note that none of them mutate
# business truth: confirming a delivery preference is not the same as executing a reschedule,
# which only ShopDeck BS can do.
ALLOWED_ACTIONS = [
    "explain_why_this_call",
    "answer_question_from_authoritative_context_only",
    "state_fact_unavailable_when_absent",
    "capture_customer_delivery_preference",
    "capture_refusal_reason",
    "acknowledge_and_return_to_delivery_topic",
    "close_call_politely",
]

# Guidance only. V1 has no server-side transition engine (see ConversationMissionContract).
ALLOWED_NEXT_STATES = [
    NDRConversationState.CUSTOMER_RESPONSE.value,
    NDRConversationState.ANSWER_CUSTOMER_QUESTION.value,
    NDRConversationState.RETURN_TO_NDR.value,
    NDRConversationState.CONFIRM_RESOLUTION.value,
    NDRConversationState.CUSTOMER_UNAVAILABLE.value,
    NDRConversationState.CUSTOMER_REFUSED.value,
    NDRConversationState.UNCLEAR.value,
    NDRConversationState.COMPLETED.value,
]

# Rendered when ShopDeck gave us no reason. We say we don't know rather than inventing one.
_REASON_UNAVAILABLE = "the delivery attempt did not succeed (the exact reason is unavailable)"


def _describe_reason(queue_item: Dict[str, Any]) -> str:
    """Renders the failure reason from business truth, or admits it is unknown."""
    reason = queue_item.get("ndr_reason_at_enroll")
    if reason is None or not str(reason).strip():
        return _REASON_UNAVAILABLE
    return str(reason).strip()


def _describe_attempts(queue_item: Dict[str, Any]) -> Optional[int]:
    """
    The API response the poller actually receives (NDRClaimResponse, ShopDeck BS
    backend/api/schemas/ndr_queue.py) exposes this value as `ndr_attempt_seq`, not
    `ndr_count_at_enroll` - that is only the underlying Postgres column name, used at
    enrollment time (backend/api/repositories/ndr_queue.py), and is never serialized to
    Brain. Reading the DB column name here means this always silently evaluates to None
    against the real claim response. `ndr_count_at_enroll` is checked second only as a
    defensive fallback in case a caller passes a raw DB row instead of the API response.
    """
    raw = queue_item.get("ndr_attempt_seq", queue_item.get("ndr_count_at_enroll"))
    try:
        count = int(raw)
    except (TypeError, ValueError):
        return None
    return count if count > 0 else None


def build_ndr_mission(queue_item: Dict[str, Any]) -> ConversationMissionContract:
    """
    Derives the conversation mission from a claimed ndr_queue row.

    Only fields present on the queue item are used: awb_no, ndr_reason_at_enroll,
    ndr_count_at_enroll, payment_mode. Nothing here may depend on CCC hydration.
    """
    reason = _describe_reason(queue_item)
    attempts = _describe_attempts(queue_item)

    why = f"A delivery attempt for this order failed. Reason recorded by the courier: {reason}."
    if attempts and attempts > 1:
        why += f" This order has had {attempts} failed delivery attempts."

    return ConversationMissionContract(
        conversation_mission=NDR_MISSION,
        why_this_call=why,
        primary_objective=(
            "Establish why the delivery failed, understand the customer's constraints, and "
            "reach a delivery outcome the customer actually agrees to."
        ),
        success_condition=(
            "The customer has stated a delivery preference (a workable delivery arrangement, "
            "or an explicit refusal) and it has been captured. Merely answering the customer's "
            "questions is NOT success."
        ),
        initial_state=NDRConversationState.INTRODUCE_REASON.value,
        allowed_actions=list(ALLOWED_ACTIONS),
        allowed_next_states=list(ALLOWED_NEXT_STATES),
        conversation_priority=(
            "The customer's immediate question always takes priority in the moment. The NDR "
            "objective is never abandoned, only deferred until the question is answered."
        ),
        return_to_mission=(
            "After answering a question: acknowledge the answer, then return to the failed "
            "delivery in the same turn, naturally and without pressure. Never ask a generic "
            "'is there anything else I can help you with?'. Never repeat a resolution request "
            "the customer has already declined."
        ),
    )
