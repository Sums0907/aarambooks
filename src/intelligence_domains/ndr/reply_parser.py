from typing import Optional, Any, Dict, Tuple
from pydantic import BaseModel, Field
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
import logging
import uuid

logger = logging.getLogger(__name__)

class ParsedOutcome(BaseModel):
    intent: str = Field(description="The customer's core intent. Must be one of: RESCHEDULE, RTO_CONFIRMED, ADDRESS_CORRECTION, UNCLEAR")
    reschedule_date: Optional[str] = Field(None, description="If intent is RESCHEDULE, extract the target date in YYYY-MM-DD format if provided, else leave null.")
    address_notes: Optional[str] = Field(None, description="If intent is ADDRESS_CORRECTION, extract any landmark or address details provided.")
    action_to_take: str = Field(description="A short instruction for the operations team for the ATR. E.g. 'Update date to 2026-10-14' or 'Mark as RTO'.")

class CustomerReplyParser:
    def __init__(self, gateway: ModelGatewayProvider):
        self.gateway = gateway
        # Since user is using a local Qwen model, we specify it as the gateway target.
        # However, the LiteLLM gateway abstract base handles routing, so we can pass a generic identifier 
        # or the exact litellm identifier if known. The generic 'default' usually maps to the configured litellm target.
        self.model = "qwen-coder" 

    async def parse_reply(self, raw_message: str) -> ParsedOutcome:
        """
        Uses the ModelGateway to parse an unstructured customer reply into a structured outcome.
        """
        prompt = (
            "You are an e-commerce customer support AI. "
            "A delivery failed and we asked the customer what they want to do. "
            "Analyze the customer's raw reply and extract their intent.\n\n"
            f"Customer Reply: '{raw_message}'\n\n"
            "Extract the intent, date (if any), address notes (if any), and summarize the action to take.\n"
            "Return ONLY a valid JSON object matching the ParsedOutcome schema."
        )

        request = GatewayGenerationRequest(
            messages=[GatewayMessage(role="user", content=prompt)],
            model=None,
            temperature=0.0
        )

        try:
            response = await self.gateway.generate(request)
            
            # Use Pydantic to parse the raw JSON string returned by the LLM
            import json
            raw_json = response.content.strip()
            # Handle markdown code block wrapping
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:-3].strip()
                
            data = json.loads(raw_json)
            parsed = ParsedOutcome(**data)
            logger.info(f"Successfully parsed customer reply into intent: {parsed.intent}")
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to parse customer reply via LLM: {e}")
            return ParsedOutcome(
                intent="UNCLEAR",
                action_to_take="Human review required: LLM parsing failed."
            )


# ---------------------------------------------------------------------------
# Deterministic heuristic fallback
# ---------------------------------------------------------------------------
# CustomerReplyParser above is the intended path, but it needs a ModelGateway and is not
# available inside the Exotel transcript webhook. The heuristic below is the synchronous
# fallback used there.
#
# It matches on WORD BOUNDARIES. The previous inline implementation in the webhook used
# plain substring matching, so "no" matched "know", "now", "north" and "nothing" - every
# customer who said "now" was classified as RTO_CONFIRMED and had their order cancelled.
# On Hindi/English mixed transcripts that fires constantly. Do not reintroduce `in` here.

import re as _re

from src.intelligence_domains.ndr.models import NDRConversationState

# Ordered most-specific first: a refusal beats a date mention, because "no, not tomorrow"
# is a refusal, not a reschedule.
_REFUSAL_PATTERNS = [
    r"\bcancel\b", r"\bcancelled\b", r"\brefuse[d]?\b", r"\breturn it\b",
    r"\bdon'?t want\b", r"\bdo not want\b", r"\bnot interested\b",
    r"\bनहीं चाहिए\b", r"\bकैंसिल\b", r"\bवापस\b",
]
_UNAVAILABLE_PATTERNS = [
    r"\bbusy\b", r"\bcall (me )?later\b", r"\bcall back\b", r"\bnot available\b",
    r"\bout of town\b", r"\btravell?ing\b",
    r"\bबाद में\b", r"\bव्यस्त\b",
]
_RESCHEDULE_PATTERNS = [
    r"\btomorrow\b", r"\bschedule\b", r"\breschedule\b", r"\bdeliver\b",
    r"\bmonday\b", r"\btuesday\b", r"\bwednesday\b", r"\bthursday\b",
    r"\bfriday\b", r"\bsaturday\b", r"\bsunday\b",
    r"\bकल\b", r"\bभेज\b", r"\bडिलीवरी\b",
]


_NEGATION_PATTERNS = [
    r"\bnot\b", r"\bcan'?t\b", r"\bcannot\b", r"\bwon'?t\b", r"\bunable\b",
    r"\bno\b", r"\bनहीं\b", r"\bना\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(_re.search(p, text, _re.IGNORECASE | _re.UNICODE) for p in patterns)


def classify_reply_heuristic(raw_transcript: str) -> tuple[str, str]:
    """
    Classifies a raw transcript into (intent, conversation_state) without an LLM.

    Returns intent from: RESCHEDULE | RTO_CONFIRMED | CUSTOMER_UNAVAILABLE | UNCLEAR
    and the NDR conversation state that intent implies.

    This is intentionally conservative: anything it cannot confidently place becomes
    UNCLEAR, which routes to human review rather than mutating the order.
    """
    text = (raw_transcript or "").strip()
    if not text:
        return "UNCLEAR", NDRConversationState.UNCLEAR.value

    if _matches_any(text, _REFUSAL_PATTERNS):
        return "RTO_CONFIRMED", NDRConversationState.CUSTOMER_REFUSED.value
    if _matches_any(text, _UNAVAILABLE_PATTERNS):
        return "CUSTOMER_UNAVAILABLE", NDRConversationState.CUSTOMER_UNAVAILABLE.value
    if _matches_any(text, _RESCHEDULE_PATTERNS):
        # A scheduling word next to a negation is a CONSTRAINT, not an agreement:
        # "no, not tomorrow" and "I can't take it Monday" must never be recorded as
        # customer_intent=agreed. Route them to human review instead.
        if _matches_any(text, _NEGATION_PATTERNS):
            return "UNCLEAR", NDRConversationState.CUSTOMER_RESPONSE.value
        return "RESCHEDULE", NDRConversationState.CONFIRM_RESOLUTION.value
    return "UNCLEAR", NDRConversationState.UNCLEAR.value


# ShopDeck's NDRIntelligenceRequest constrains these vocabularies
# (business_systems/shopdeck/backend/api/schemas/ndr_queue.py):
#   recommended_action: reschedule|accept_rto|escalate|no_action
#   customer_intent:    agreed|declined|unreachable|unclear
_SHOPDECK_MAPPING = {
    "RESCHEDULE":           ("reschedule",  "agreed"),
    "RTO_CONFIRMED":        ("accept_rto",  "declined"),
    "CUSTOMER_UNAVAILABLE": ("escalate",    "unreachable"),
    "UNCLEAR":              ("escalate",    "unclear"),
}


def to_shopdeck_vocabulary(intent: str) -> tuple[str, str]:
    """Maps an internal intent to ShopDeck's (recommended_action, customer_intent) pair."""
    return _SHOPDECK_MAPPING.get(intent, ("escalate", "unclear"))


# ---------------------------------------------------------------------------
# Matching a RESCHEDULE reply against the two specific dates actually offered
# ---------------------------------------------------------------------------
# Priya only ever offers exactly two real dates (offered_reattempt_date_1/_2 -
# ccc_builder.py, confirmed directly against ShopDeck's own NDR console). A generic
# RESCHEDULE classification from classify_reply_heuristic() is not enough for the
# writeback to be useful to ShopDeck's ops team - they need to know WHICH of the two
# dates was actually agreed to. Kept as a separate, additive function (not folded into
# classify_reply_heuristic's return signature) so existing 2-tuple callers/tests are
# unaffected.

_WEEKDAY_RE = _re.compile(r"^([A-Za-z]+)")


def _weekday_of(offered_date: Optional[str]) -> Optional[str]:
    """Extracts 'Wednesday' from 'Wednesday (09-09-2026)'."""
    if not offered_date:
        return None
    m = _WEEKDAY_RE.match(offered_date.strip())
    return m.group(1) if m else None


def extract_matched_reattempt_date(
    raw_transcript: str,
    offered_date_1: Optional[str],
    offered_date_2: Optional[str],
) -> Optional[str]:
    """
    Returns whichever of offered_date_1 / offered_date_2 the transcript actually names, or
    None if neither is identifiable. Deliberately does not guess: a RESCHEDULE-classified
    reply that doesn't name either specific date returns None, since the whole point of the
    two-fixed-dates design is to know exactly which day was agreed to, not just that the
    customer said yes to something.

    date_1 is always "tomorrow" (today+1) and date_2 is always "day after tomorrow"
    (today+2) under the current NDR reschedule-window config (see
    src/intelligence_domains/ndr/config.py), so generic tomorrow/day-after-tomorrow
    phrasing (English and Hindi) is matched in addition to the literal weekday name.
    """
    text = (raw_transcript or "").strip()
    if not text:
        return None

    weekday_1 = _weekday_of(offered_date_1)
    weekday_2 = _weekday_of(offered_date_2)

    # Both Devanagari and romanized Hinglish forms are matched - real transcripts (STT
    # output especially) render Hindi in either script depending on the engine, and
    # romanized "kal"/"parso" are extremely common in real Hinglish speech. Devanagari
    # terms use plain substring matching, not \b-bounded regex: Python's \b is unreliable
    # at the edge of Devanagari combining marks (e.g. the anusvara in "परसों"), which
    # silently made \bपरसों\b never match at all. Safe here since these are distinctive
    # multi-syllable words, unlike the short-ASCII-word collision risk (e.g. "no" inside
    # "know") that word-boundary matching elsewhere in this file specifically guards against.
    matches_1 = (weekday_1 and _re.search(rf"\b{_re.escape(weekday_1)}\b", text, _re.IGNORECASE)) or \
        _re.search(r"\btomorrow\b|\bkal\b", text, _re.IGNORECASE) or "कल" in text
    matches_2 = (weekday_2 and _re.search(rf"\b{_re.escape(weekday_2)}\b", text, _re.IGNORECASE)) or \
        _re.search(r"\bday after tomorrow\b|\bparso\b", text, _re.IGNORECASE) or "परसों" in text

    # If both patterns fire (e.g. the customer said "tomorrow" but the weekday name for
    # date_2 happens to also appear as an unrelated word), prefer an explicit weekday-name
    # match over the generic tomorrow/day-after-tomorrow phrasing, since it's less ambiguous.
    if weekday_2 and _re.search(rf"\b{_re.escape(weekday_2)}\b", text, _re.IGNORECASE):
        return offered_date_2
    if weekday_1 and _re.search(rf"\b{_re.escape(weekday_1)}\b", text, _re.IGNORECASE):
        return offered_date_1
    if matches_2:
        return offered_date_2
    if matches_1:
        return offered_date_1
    return None


# ---------------------------------------------------------------------------
# Shared, provider-agnostic NDR outcome recording
# ---------------------------------------------------------------------------
# Extracted out of Exotel's handle_transcript() webhook handler
# (src/api/webhooks/exotel_webhooks.py) so a second voice-bot provider (e.g. Sarvam) can
# reuse the exact same classification/matching/recording behavior instead of duplicating
# it. Behavior is unchanged from the original inline version - same logging, same
# last-decisive-turn-wins semantics (record_pending_ndr_outcome always overwrites; the
# actual one-time submission to ShopDeck happens at session-end).
#
# Deliberately takes a plain repo + engagement_id + raw_transcript, not a provider-specific
# payload shape - each provider's webhook handler is responsible for extracting the
# transcript text out of its own payload format first (see extract_customer_utterance() for
# Exotel's) and resolving engagement_id via its own provider correlation, then calling this.

async def record_ndr_outcome_from_transcript(repo, engagement_id: str, raw_transcript: str) -> None:
    """
    Classifies a customer transcript turn and records it as the current pending NDR
    outcome for this engagement, if it represents a decisive answer.

    An UNCLEAR classification is a no-op: it must never overwrite a real prior answer with
    "I didn't understand". Any exception is caught and logged, never raised, so a
    classification failure cannot break the caller's webhook response.
    """
    try:
        if not raw_transcript:
            return

        intent, conversation_state = classify_reply_heuristic(raw_transcript)

        if intent == "UNCLEAR":
            logger.info(
                "Transcript classified UNCLEAR for engagement %s; leaving prior "
                "pending NDR outcome (if any) untouched.",
                engagement_id,
            )
            return

        engagement = await repo.get_engagement(engagement_id)
        # CustomerEngagementRecord has no metadata field - queue_item_id is stored
        # in call_context by the poller (src/workers/ndr_queue_poller.py) at dispatch time.
        call_context_for_lookup = (engagement or {}).get("call_context", {}) or {}
        queue_item_id = call_context_for_lookup.get("queue_item_id")
        awb_no = (engagement or {}).get("awb_no")

        if not queue_item_id or not awb_no or awb_no == "UNKNOWN":
            logger.error(
                "Cannot record NDR outcome for engagement %s: "
                "unresolved queue_item_id=%r awb_no=%r",
                engagement_id, queue_item_id, awb_no,
            )
            return

        matched_reattempt_date = None
        if intent == "RESCHEDULE":
            # offered_reattempt_date_1/2 live on NDRConversationProjection, which is
            # what the poller now stores as call_context - not on ccc_snapshot (the raw
            # CCC, which never had these fields).
            matched_reattempt_date = extract_matched_reattempt_date(
                raw_transcript,
                call_context_for_lookup.get("offered_reattempt_date_1"),
                call_context_for_lookup.get("offered_reattempt_date_2"),
            )

        await repo.record_pending_ndr_outcome(engagement_id, {
            "queue_item_id": queue_item_id,
            "awb_no": awb_no,
            "intent": intent,
            "conversation_state": conversation_state,
            "raw_transcript": raw_transcript,
            "matched_reattempt_date": matched_reattempt_date,
        })
        logger.info(
            "Recorded pending NDR outcome for engagement %s: state=%s "
            "(will submit at session-end if this is still current)",
            engagement_id, conversation_state,
        )
    except Exception as e:
        logger.exception("NDR outcome recording raised for engagement %s: %s", engagement_id, e)


# ---------------------------------------------------------------------------
# Shared, provider-agnostic ShopDeck writeback enqueue
# ---------------------------------------------------------------------------
# Extracted out of Exotel's _submit_pending_ndr_outcome() (src/api/webhooks/
# exotel_webhooks.py) - the CAS-claim + idempotent-enqueue mechanics are identical
# regardless of how the outcome was decided (Exotel: heuristic classification of the final
# transcript turn; Sarvam: the voice agent's own LLM decides the outcome directly and
# reports it via a tool call). Only the caller differs in how it arrives at
# recommended_action/customer_intent/diagnosis/action_parameters - the durability contract
# below (see _submit_pending_ndr_outcome's original docstring) is shared unchanged.

_NDR_RESULT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


async def enqueue_ndr_intelligence_result(
    repo,
    *,
    engagement_id: str,
    queue_item_id: str,
    awb_no: str,
    recommended_action: str,
    customer_intent: str,
    diagnosis: str,
    reasoning: str,
    provenance: str,
    action_parameters: Optional[Dict[str, Any]] = None,
) -> None:
    """
    The one shared path for enqueuing an NDR intelligence outcome for ShopDeck delivery,
    used by every voice provider's webhook/hook handler. See _submit_pending_ndr_outcome
    (exotel_webhooks.py) for the full durability invariant this implements: CAS claim is
    atomic, enqueue is idempotent (unique result_id index), and any non-duplicate-key
    failure must propagate so the caller's webhook returns a non-2xx and the provider
    retries delivery.
    """
    result_id = f"res_{uuid.uuid5(_NDR_RESULT_NAMESPACE, f'{engagement_id}:{diagnosis}').hex}"

    won_claim = await repo.claim_intelligence_writeback(engagement_id, result_id)
    if not won_claim:
        logger.info(
            "NDR writeback CAS already claimed: engagement_id=%s result_id=%s "
            "(duplicate delivery) - attempting idempotent re-enqueue.",
            engagement_id, result_id,
        )

    intelligence_payload = {
        "result_id": result_id,
        "queue_item_id": queue_item_id,
        "engagement_id": engagement_id,
        "awb_no": awb_no,
        "recommended_action": recommended_action,
        "customer_intent": customer_intent,
        "diagnosis": diagnosis,
        "confidence_level": "low",
        "provenance": provenance,
        "reasoning": reasoning,
        "submitted_by": "brain_core_rabta",
        "action_parameters": action_parameters or {},
    }

    enqueued = await repo.enqueue_intelligence_writeback(intelligence_payload, engagement_id)
    if enqueued:
        logger.info(
            "NDR writeback enqueued: engagement_id=%s result_id=%s state=%s action=%s",
            engagement_id, result_id, diagnosis, recommended_action,
        )
    else:
        logger.info(
            "NDR writeback already enqueued (idempotent): engagement_id=%s result_id=%s",
            engagement_id, result_id,
        )


# Sarvam's custom on-end tool reports call_outcome directly - the agent's own LLM already
# decided the outcome, unlike Exotel's raw-transcript path which needs
# classify_reply_heuristic() to derive one. This maps that outcome straight onto ShopDeck's
# (recommended_action, customer_intent) vocabulary plus a diagnosis, by user decision
# (2026-09-12):
#   - address_updated/phone_no_update map to "reschedule", not "no_action" - even when only
#     an address/phone correction was given (no date confirmed), the order still needs a
#     real delivery attempt, so it belongs in the "needs action" bucket ops already
#     monitors, not a bucket that reads as "nothing to do."
#   - escalation_requested/no_resolution both fall back to escalate/unclear - ShopDeck's
#     customer_intent vocabulary has no "wants a human" value, so unclear is the
#     least-wrong fit (unreachable would be actively wrong - the customer was on the call).
_SARVAM_CALL_OUTCOME_MAPPING: Dict[str, Tuple[str, str, str]] = {
    "rescheduled": ("reschedule", "agreed", NDRConversationState.CONFIRM_RESOLUTION.value),
    "customer_declined": ("accept_rto", "declined", NDRConversationState.CUSTOMER_REFUSED.value),
    "address_updated": ("reschedule", "agreed", NDRConversationState.CONFIRM_RESOLUTION.value),
    "phone_no_update": ("reschedule", "agreed", NDRConversationState.CONFIRM_RESOLUTION.value),
    "escalation_requested": ("escalate", "unclear", NDRConversationState.UNCLEAR.value),
    "no_resolution": ("escalate", "unclear", NDRConversationState.UNCLEAR.value),
}


def map_sarvam_call_outcome(call_outcome: str) -> Tuple[str, str, str]:
    """
    Returns (recommended_action, customer_intent, diagnosis) for a Sarvam call_outcome
    value. An unrecognized value falls back to the same escalate/unclear pair as
    no_resolution/escalation_requested - a malformed or unexpected value from the agent
    must route to human review, not crash the outcome handler or silently mis-file the
    order under a fabricated label.
    """
    return _SARVAM_CALL_OUTCOME_MAPPING.get(
        call_outcome,
        ("escalate", "unclear", NDRConversationState.UNCLEAR.value),
    )
