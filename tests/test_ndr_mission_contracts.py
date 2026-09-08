"""
Deterministic gating tier for the NDR Conversation Mission/State Contract.

These tests start from a raw ndr_queue row and run the real pipeline
(mission_factory -> ConversationalDirective -> CCC -> project() -> session_constants).
They deliberately do NOT hand-construct a CustomerConversationProjection: doing so would
stop them detecting the two failure modes this contract is most likely to regress into --
a mission built from data the poller does not yet have, and a mission that never reaches
the call because the webhook allow-list was not updated.

No LLM is involved. Everything here is reproducible and safe to gate on.
"""

import pytest

from src.brain_core.action_engine.contracts import (
    ConversationalDirective,
    ConversationMissionContract,
)
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.brain_core.context_engine.ccc_contracts import (
    CustomerContext,
    CustomerConversationContext,
    OrderContext,
    ProductContext,
)
from src.intelligence_domains.ndr.mission_factory import (
    NDR_MISSION,
    NDRConversationState,
    build_ndr_mission,
)
from src.intelligence_domains.ndr.reply_parser import (
    classify_reply_heuristic,
    to_shopdeck_vocabulary,
)

# Shaped like the real NDRClaimResponse the poller receives over the API
# (business_systems/shopdeck/backend/api/schemas/ndr_queue.py), not the raw ndr_queue
# Postgres row - the attempt count is serialized as `ndr_attempt_seq`, not
# `ndr_count_at_enroll` (that name exists only as a DB column, never on the wire).
QUEUE_ITEM = {
    "queue_item_id": "q-1",
    "awb_no": "AWB123",
    "ndr_reason_at_enroll": "Customer unavailable",
    "ndr_attempt_seq": 2,
    "payment_mode": "cod",
}


def _ccc(mission: ConversationMissionContract) -> CustomerConversationContext:
    """Builds a CCC the way the poller does, without touching ShopDeck."""
    directive = ConversationalDirective(
        objective=mission.primary_objective,
        context_summary=mission.why_this_call,
        allowed_actions=mission.allowed_actions,
        constraints=["Never state a fact that is not present in the authoritative context."],
        mission=mission,
    )
    return CustomerConversationContext(
        ccc_id="ccc_test",
        target_identity=QUEUE_ITEM["awb_no"],
        customer_profile=CustomerContext(name="Rahul", phone="9999999999"),
        order_facts=OrderContext(
            awb_no=QUEUE_ITEM["awb_no"],
            collectable_amount=499.0,
            payment_mode="cod",
            past_delivery_attempts=2,
        ),
        product_context=ProductContext(product_name="Cotton Bedsheet"),
        directive=directive,
    )


# ---------------------------------------------------------------------------
# 1. The mission contract itself
# ---------------------------------------------------------------------------

def test_all_nine_spec_states_exist_with_exact_names():
    """The approved V1 vocabulary. RETURN_TO_NDR carries requirements 8 and 10."""
    assert [s.value for s in NDRConversationState] == [
        "INTRODUCE_REASON",
        "CUSTOMER_RESPONSE",
        "ANSWER_CUSTOMER_QUESTION",
        "RETURN_TO_NDR",
        "CONFIRM_RESOLUTION",
        "CUSTOMER_UNAVAILABLE",
        "CUSTOMER_REFUSED",
        "UNCLEAR",
        "COMPLETED",
    ]


def test_mission_is_built_from_queue_item_alone():
    """
    Guards the ordering bug: the mission must be derivable before CCC hydration runs,
    so it may only read fields present on the claimed queue row.
    """
    mission = build_ndr_mission(QUEUE_ITEM)
    assert mission.conversation_mission == NDR_MISSION
    assert "Customer unavailable" in mission.why_this_call
    assert "2 failed delivery attempts" in mission.why_this_call
    assert mission.initial_state == NDRConversationState.INTRODUCE_REASON.value
    assert mission.allowed_next_states, "allowed_next_states is required by the contract"


def test_missing_reason_is_declared_unavailable_never_invented():
    mission = build_ndr_mission({"awb_no": "AWB999"})
    assert "unavailable" in mission.why_this_call.lower()


def test_mission_is_immutable():
    mission = build_ndr_mission(QUEUE_ITEM)
    with pytest.raises(Exception):
        mission.initial_state = NDRConversationState.COMPLETED.value


def test_mission_is_the_single_authority_for_allowed_actions():
    """Resolves the duplicate-field collision: exactly one list reaches the call."""
    mission = build_ndr_mission(QUEUE_ITEM)
    directive = ConversationalDirective(
        objective="x", context_summary="y",
        allowed_actions=["STALE_DIRECTIVE_LIST"],
        constraints=[], mission=mission,
    )
    assert directive.effective_allowed_actions == mission.allowed_actions
    assert "STALE_DIRECTIVE_LIST" not in directive.effective_allowed_actions


# ---------------------------------------------------------------------------
# 2. The mission survives projection into session_constants
# ---------------------------------------------------------------------------

MISSION_KEYS = [
    "mission_conversation_mission",
    "mission_why_this_call",
    "mission_primary_objective",
    "mission_success_condition",
    "mission_initial_state",
    "mission_allowed_next_states",
    "mission_conversation_priority",
    "mission_return_to_mission",
]


def test_projection_carries_every_mission_field_as_a_flat_scalar():
    builder = CustomerConversationContextBuilder(provider=None)
    projection = builder.project(_ccc(build_ndr_mission(QUEUE_ITEM)))
    dumped = projection.model_dump()
    for key in MISSION_KEYS:
        assert dumped.get(key), f"{key} missing from projection"
        assert isinstance(dumped[key], str), f"{key} must be a flat scalar, not {type(dumped[key])}"


def test_every_mission_field_reaches_the_exotel_session_constants_allow_list():
    """
    The allow-list in exotel_webhooks.py is hardcoded. If a mission field is added to the
    projection but not to that list, the mission silently never reaches Priya while every
    other test still passes. This is that guard.
    """
    import inspect
    from src.api.webhooks import exotel_webhooks

    source = inspect.getsource(exotel_webhooks.build_session_constants)
    for key in MISSION_KEYS:
        assert f'"{key}"' in source, f"{key} is not in the session_constants allow-list"


# ---------------------------------------------------------------------------
# 3. The greeting
# ---------------------------------------------------------------------------

def _greet(**call_context):
    from src.api.webhooks.exotel_webhooks import generate_dynamic_greeting
    return generate_dynamic_greeting({"call_context": call_context})


def test_greeting_is_deterministic():
    ctx = dict(customer_name="Rahul", product_name="Cotton Bedsheet")
    assert len({_greet(**ctx) for _ in range(25)}) == 1


def test_greeting_states_the_failed_delivery_and_never_opens_with_how_can_i_help():
    """
    Checks the requirement (a stated delivery failure), not one specific wording of it -
    the greeting legitimately evolved to voice the real failure reason (why_failed) instead
    of withholding it, which changed the exact phrase without changing the requirement.
    """
    greeting = _greet(customer_name="Rahul", product_name="Cotton Bedsheet")
    assert "नहीं हो पाई" in greeting
    assert "प्रिया" in greeting
    for banned in ["How can I help", "कैसे मदद", "आपकी क्या मदद"]:
        assert banned not in greeting


def test_greeting_ends_with_consent_and_contains_no_reschedule_ask():
    """
    Requirement 9: establish context first. The date ask comes later, or not at all.

    "कल" is deliberately NOT banned here: Hindi "कल" is tense-ambiguous (yesterday/tomorrow),
    and the greeting legitimately uses it in the past tense to describe WHEN the delivery
    failed ("delivery कल नहीं हो पाई" - "delivery didn't happen yesterday"), which is not a
    reschedule proposal. What must never appear is an actual forward-looking date ask.
    """
    greeting = _greet(customer_name="Rahul", product_name="Cotton Bedsheet")
    assert greeting.rstrip().endswith("क्या अभी बात करना सुविधाजनक है?")
    for pushy in ["tomorrow", "reschedule", "available to receive", "Should we reschedule"]:
        assert pushy not in greeting


def test_greeting_omits_absent_facts_rather_than_guessing():
    greeting = _greet()
    assert "None" not in greeting
    assert "नहीं हो पाई" in greeting


# ---------------------------------------------------------------------------
# 4. Transcript intent classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("transcript", ["I know", "send it now", "north side", "nothing yet"])
def test_substring_no_never_cancels_an_order(transcript):
    """
    Regression: the old substring match classified 'know'/'now'/'north' as RTO_CONFIRMED,
    cancelling orders for customers who said 'now'.
    """
    intent, _ = classify_reply_heuristic(transcript)
    assert intent != "RTO_CONFIRMED"


@pytest.mark.parametrize("transcript", ["no, not tomorrow", "I cannot receive tomorrow"])
def test_scheduling_constraint_is_never_recorded_as_agreement(transcript):
    """Scenario H: 'I can't take it tomorrow' is a constraint, not consent."""
    intent, _ = classify_reply_heuristic(transcript)
    _, customer_intent = to_shopdeck_vocabulary(intent)
    assert customer_intent != "agreed"


def test_terminal_outcomes_map_to_shopdeck_vocabulary():
    """ShopDeck constrains these enums; a free-text value 422s the writeback."""
    valid_actions = {"reschedule", "accept_rto", "escalate", "no_action"}
    valid_intents = {"agreed", "declined", "unreachable", "unclear"}
    for transcript, expected_state in [
        ("please cancel it", NDRConversationState.CUSTOMER_REFUSED.value),
        ("I am busy, call me later", NDRConversationState.CUSTOMER_UNAVAILABLE.value),
        ("yes tomorrow is fine", NDRConversationState.CONFIRM_RESOLUTION.value),
    ]:
        intent, state = classify_reply_heuristic(transcript)
        action, customer_intent = to_shopdeck_vocabulary(intent)
        assert state == expected_state
        assert action in valid_actions
        assert customer_intent in valid_intents


def test_empty_transcript_is_unclear_not_a_business_decision():
    assert classify_reply_heuristic("") == ("UNCLEAR", NDRConversationState.UNCLEAR.value)
