from typing import Optional, Any
from pydantic import BaseModel, Field
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
import logging

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

from src.intelligence_domains.ndr.mission_factory import NDRConversationState

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
