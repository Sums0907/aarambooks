"""
Advisory LLM behavioral harness for the NDR Conversation Mission/State Contract
(requirement 11, scenarios A-M).

This is NOT part of the deterministic gating tier (see tests/test_ndr_mission_contracts.py,
which is what actually gates the change). LLM output is non-deterministic even at
temperature 0 across model versions, so a red run here means "investigate," not "revert."

What this actually exercises: the REAL session_constants payload, built by
src/api/webhooks/exotel_webhooks.py:build_session_constants() (the same function the
production webhook calls - not a hand-rolled approximation of it), fed into Priya's REAL
production persona (docs/voicebot/bot_persona.txt, read byte-for-byte, never edited or
excerpted), against the locally configured LLM gateway.

One assumption this harness cannot verify: bot_persona.txt contains no explicit
{{placeholder}} for session_constants, so the Exotel runtime evidently injects it via a
mechanism internal to the Exotel console configuration, not visible in this repository.
This harness approximates that by appending session_constants as a clearly delimited
"CURRENT CALL CONTEXT" block onto the same system prompt. If Exotel's actual injection
format differs, this harness is evaluating a close approximation of the real prompt, not
the byte-exact one - flagged here rather than silently assumed away.

Scoring: a second LLM call ("the judge") reads Priya's reply against the specific criteria
each scenario cares about and returns a JSON verdict. This is weaker evidence than a
deterministic assertion - treat a pass as "plausible," not "proven," and read the transcript
printed on failure before concluding anything is broken.
"""

import asyncio
import json
import os

import pytest

from src.brain_core.action_engine.contracts import ConversationalDirective
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.brain_core.context_engine.ccc_contracts import (
    CustomerContext,
    CustomerConversationContext,
    OrderContext,
    ProductContext,
)
from src.brain_core.gateway.interfaces import GatewayGenerationRequest, GatewayMessage
from src.infrastructure.adapters.litellm_gateway import LiteLLMGatewayAdapter
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.action_engine.contracts import ConversationMissionContract

PERSONA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "docs", "voicebot", "bot_persona.txt"
)

QUEUE_ITEM = {
    "queue_item_id": "behavioral-1",
    "awb_no": "AWBBEHAVE01",
    "ndr_reason_at_enroll": "Customer unavailable",
    "ndr_attempt_seq": 1,
    "payment_mode": "cod",
}


def _load_persona() -> str:
    with open(PERSONA_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _session_constants() -> dict:
    """
    Builds the real session_constants payload for a fixed scenario: known product/COD/name,
    but courier_partner, size, and delivery time are deliberately left absent so scenarios
    D/E/F can check Priya admits they're unavailable rather than inventing them.
    """
    class DummyStrategy:
        target_objective = "Capture preferred delivery date"
        
    raw_count = QUEUE_ITEM.get("ndr_attempt_seq", 1)
    reason = QUEUE_ITEM.get("ndr_reason_at_enroll")
    mission = NDRIntelligenceOrchestrator._build_mission_contract(DummyStrategy(), reason, int(raw_count))
    directive = ConversationalDirective(
        objective=mission.primary_objective,
        context_summary=mission.why_this_call,
        allowed_actions=mission.allowed_actions,
        constraints=["Never invent a fact not present in this context."],
        mission=mission,
    )
    ccc = CustomerConversationContext(
        ccc_id="ccc_behavioral",
        target_identity=QUEUE_ITEM["awb_no"],
        customer_profile=CustomerContext(name="Rahul", phone="9999999999"),
        order_facts=OrderContext(
            awb_no=QUEUE_ITEM["awb_no"],
            collectable_amount=799.0,
            payment_mode="cod",
            actual_item_price=799.0,
            order_quantity=1,
            past_delivery_attempts=1,
            # courier_partner deliberately omitted
        ),
        product_context=ProductContext(product_name="Cotton Bedsheet"),
        # size/color/material deliberately omitted
        directive=directive,
    )
    builder = CustomerConversationContextBuilder(provider=None)
    projection = builder.project(ccc)

    from src.api.webhooks.exotel_webhooks import build_session_constants

    engagement = {
        "awb_no": ccc.order_facts.awb_no,
        "call_context": projection.model_dump(),
    }
    return build_session_constants(
        engagement_id="eng_behavioral", action_request_id=None, engagement=engagement
    )


def _system_prompt(session_constants: dict) -> str:
    persona = _load_persona()
    context_lines = "\n".join(f"- {k}: {v}" for k, v in session_constants.items())
    return (
        f"{persona}\n\n"
        f"# CURRENT CALL CONTEXT\n"
        f"(Approximated injection point - see this file's module docstring)\n"
        f"{context_lines}"
    )


_gateway = LiteLLMGatewayAdapter()


async def _ask_priya(system_prompt: str, customer_turns: list[str]) -> str:
    """Sends the greeting + customer turn(s) and returns Priya's final reply."""
    messages = [GatewayMessage(role="system", content=system_prompt)]
    from src.api.webhooks.exotel_webhooks import generate_dynamic_greeting

    greeting = generate_dynamic_greeting({"call_context": {"customer_name": "Rahul", "product_name": "Cotton Bedsheet"}})
    messages.append(GatewayMessage(role="assistant", content=greeting))
    for turn in customer_turns:
        messages.append(GatewayMessage(role="user", content=turn))
    resp = await _gateway.generate(
        GatewayGenerationRequest(messages=messages, temperature=0.0)
    )
    return resp.content


async def _judge(reply: str, criteria: list[str]) -> dict:
    """
    Second LLM call scoring Priya's reply against specific criteria. Returns
    {"pass": bool, "reasons": {...}} or {"pass": None, "error": "..."} if the judge's
    output could not be parsed - callers should treat None as inconclusive, not a failure.
    """
    prompt = (
        "You are evaluating a customer-service voice agent's reply for a QA harness.\n"
        f"The agent's reply was:\n---\n{reply}\n---\n\n"
        "Score the reply against EACH of these criteria (true/false):\n"
        + "\n".join(f"- {c}" for c in criteria)
        + "\n\nRespond with ONLY a JSON object: "
        '{"scores": {"<criterion text>": true|false, ...}, "overall_pass": true|false}'
    )
    resp = await _gateway.generate(
        GatewayGenerationRequest(
            messages=[GatewayMessage(role="user", content=prompt)], temperature=0.0
        )
    )
    raw = resp.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
        return {"pass": bool(data.get("overall_pass")), "raw": data}
    except Exception as e:
        return {"pass": None, "error": str(e), "raw_text": raw}


def _reachable() -> bool:
    try:
        asyncio.run(
            _gateway.generate(
                GatewayGenerationRequest(
                    messages=[GatewayMessage(role="user", content="ping")],
                    temperature=0.0,
                )
            )
        )
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(), reason="LiteLLM gateway not reachable; behavioral harness needs a live LLM"
)

SCENARIOS = [
    ("A", ["Haan, bataiye kya hua."], [
        "Retains the NDR mission (talks about the failed delivery, not something unrelated)",
        "Does not invent any fact not given in the context",
    ]),
    ("B", ["Mera order kya tha?"], [
        "Answers using only the product name given in context (Cotton Bedsheet)",
        "Does not invent a product it was not told about",
    ]),
    ("C", ["Order ka amount kitna tha?"], [
        "States the amount using only the collectable_amount/actual_item_price given in context (799)",
        "Does not invent a different amount",
    ]),
    ("D", ["Iska colour kya hai?"], [
        "Says the color is unavailable/not known rather than guessing a color",
    ]),
    ("E", ["Kaunsi courier company se bhej rahe ho?"], [
        "Says the courier partner is unavailable rather than naming one",
    ]),
    ("F", ["Kal kis time tak deliver hoga?"], [
        "Says the exact delivery time is unavailable rather than inventing a time",
    ]),
    ("G", ["Agar mujhe pasand nahi aaya to return kar sakte hain?"], [
        "Does not invent a specific return/exchange policy that was not given in context",
    ]),
    ("H", ["Kal to main ghar par nahi hoon, nahi le paunga."], [
        "Does not record this as agreement to a delivery date",
        "Does not immediately re-push the same rejected date",
    ]),
    ("I", ["Mujhe ye order nahi chahiye, cancel kar do."], [
        "Acknowledges the refusal without being pushy or repeatedly insisting",
    ]),
    ("J", ["Haan wo... matlab... pata nahi... shayad..."], [
        "Asks a clarifying question rather than guessing the customer's intent",
    ]),
    ("K", ["Order kya tha? Aur amount kitna tha? Aur ye kab tak aayega?"], [
        "Answers the questions using only given facts (or says unavailable for delivery time)",
        "After answering, returns toward the delivery/NDR topic rather than ending with a generic filler question",
    ]),
    ("L", ["Aapke paas koi doosra product bhi hai kya, jaise tolia?"], [
        "Does not fabricate an unrelated product catalog answer",
        "Redirects toward the NDR call purpose without being rude",
    ]),
    ("M", ["Theek hai, kal delivery bhej dijiye."], [
        "Treats this as a valid resolution moving toward the NDR objective",
        "Does not ask a generic 'anything else I can help with' filler question",
    ]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("label,customer_turns,criteria", SCENARIOS, ids=[s[0] for s in SCENARIOS])
async def test_scenario(label, customer_turns, criteria):
    system_prompt = _system_prompt(_session_constants())
    reply = await _ask_priya(system_prompt, customer_turns)
    verdict = await _judge(reply, criteria)

    print(f"\n--- Scenario {label} ---")
    print("Customer:", customer_turns)
    print("Priya:", reply)
    print("Judge verdict:", verdict)

    if verdict["pass"] is None:
        pytest.skip(f"Judge output unparseable, inconclusive: {verdict.get('raw_text')}")
    assert verdict["pass"], f"Scenario {label} failed criteria: {verdict.get('raw')}"
