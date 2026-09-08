# NDR Conversation Mission/State Contract — implementation report

Author: Claude (implementation)
Date: 2026-09-08
Scope: the revised plan, with the round-2 blocking corrections applied.

## What was built

### Contract layer — `src/brain_core/action_engine/contracts.py`
`ConversationMissionContract` (frozen, `extra='forbid'`) carrying **all nine** fields from
requirement 1, including `allowed_next_states`, which the revised plan had dropped.

`initial_state` is named deliberately: the object is frozen and embedded in an immutable CCC,
so it cannot represent a state that advances mid-call. **V1 has no server-side transition
engine.** `allowed_next_states` is prompt-level guidance, not an enforced transition table.
This is documented in the docstring so nobody later mistakes it for enforcement.

`ConversationalDirective.mission` added, plus `effective_allowed_actions`, which resolves the
duplicate-field collision: the mission's list wins whenever a mission is attached, so exactly
one `allowed_actions` value reaches the call.

### NDR domain — `src/intelligence_domains/ndr/mission_factory.py` (new)
`NDRConversationState` StrEnum with the **nine approved names verbatim**, including
`RETURN_TO_NDR`. The enum lives in the NDR domain, not brain_core, so the mission contract
stays domain-agnostic in shape while the NDR vocabulary is owned by NDR-ID.

`build_ndr_mission(queue_item)` is a pure function over the claimed `ndr_queue` row. It reads
only `ndr_reason_at_enroll`, `ndr_count_at_enroll`, `awb_no`, `payment_mode` — never anything
produced by CCC hydration, which is what made the original plan circular. A missing reason
renders as explicitly unavailable rather than being invented.

### Projection — `ccc_contracts.py`, `ccc_builder.py`
Eight flat scalar `mission_*` fields on `CustomerConversationProjection` (not a nested dict,
which the webhook would have `str()`-ed into a Python-repr blob). `project()` populates them
and now sources `allowed_actions` from `effective_allowed_actions`.

### Poller — `src/workers/ndr_queue_poller.py`
Builds the mission from the claimed queue item **before** constructing the action, so the
directive is complete before `ccc_builder.build()` runs. The directive's `context_summary` was
the literal string `"test"`; it now carries `mission.why_this_call`.

### Webhook — `src/api/webhooks/exotel_webhooks.py`
- Allow-list extended with all eight `mission_*` keys, with a comment stating the silent-failure
  risk. A test enforces this (see below).
- Four new behavioural instructions: `instruction_lookup_rule` (requirement 7's "never claim I
  checked"), `instruction_mission_retention`, `instruction_no_filler_loop`, `instruction_not_pushy`.
- `generate_dynamic_greeting` rewritten: deterministic (no `random.choice`), Hindi, states the
  failed delivery, ends on `क्या अभी बात करना सुविधाजनक है?`, and contains **no** delivery-date ask.
  Absent name/product are omitted, not guessed. The courier's raw failure reason is deliberately
  not read aloud — it is internal jargon, and stays in `session_constants` for use if asked.

### Intent classification — `src/intelligence_domains/ndr/reply_parser.py`
`classify_reply_heuristic()` — word-boundary regex, replacing the substring matching that made
"know", "now", "north" and "nothing" classify as `RTO_CONFIRMED` and cancel customers' orders.

A negation guard was added after testing: `"no, not tomorrow"` and `"I cannot receive tomorrow"`
initially classified as RESCHEDULE → `customer_intent="agreed"`. That is requirement 11's
scenario H being recorded as consent the customer never gave. Those now route to human review.

`to_shopdeck_vocabulary()` maps internal intents to ShopDeck's constrained enums.

## The writeback was not merely unauthenticated — it was schema-invalid

Round 2 flagged the `dummy_token`. Reading ShopDeck's actual schema
(`business_systems/shopdeck/backend/api/schemas/ndr_queue.py:55`) showed it was worse: the
webhook posted `{queue_item_id, engagement_id, ndr_intent, recommended_action, confidence_score}`
while `NDRIntelligenceRequest` **requires** `result_id` and `awb_no`, does not accept `ndr_intent`
or `confidence_score`, and constrains `recommended_action` to
`reschedule|accept_rto|escalate|no_action` — where the webhook was sending free text
("Agent determined intent: RESCHEDULE"). Every POST would have 422'd, silently, forever.

Now: correct schema, deterministic `result_id` (uuid5, so redelivered webhooks are idempotent),
`settings.shopdeck_token` for auth, terminal conversation state carried in `diagnosis`, refusal
to post when `queue_item_id`/`awb_no` cannot be resolved rather than posting `"unknown"`, and
failures logged at error with the response body instead of a swallowed `print`.

## Tests

`tests/test_ndr_mission_contracts.py` — 19 deterministic tests, no LLM. They start from a raw
queue-item dict and run the real pipeline through to the session_constants allow-list, so they
detect both the ordering bug and the allow-list drift. Notable guards:
- all nine state names present, in order
- mission derivable from the queue item alone
- every mission field reaches the webhook allow-list (asserted against the function's source)
- greeting deterministic across 25 renders; ends on the consent question; contains no date ask
- `"know"` / `"now"` / `"north"` never cancel an order
- a scheduling constraint is never recorded as `agreed`

Three existing tests asserted the old, broken contract and were updated, each with a comment
explaining why:
- `test_greeting_obeys_tomorrow_only` asserted the greeting **must** ask about tomorrow — the
  exact pushy opening requirement 9 forbids. Inverted.
- `test_ndr_queue_e2e_local` (x2) asserted `ndr_intent`, a field ShopDeck does not accept, and
  mocked engagements with no `awb_no`, which ShopDeck requires.

One pre-existing test bug was fixed: `test_ndr_queue_e2e_4_items` mocked
`exotel_adapter.execute`, but the poller calls `executor.dispatch_provider_call`
(`executor.py:61`). It was failing at HEAD and now passes.

### Execution evidence

```
baseline (HEAD, clean worktree):  17 failed, 411 passed, 8 errors
after this change:                18 failed, 432 passed, 8 errors
```

- `tests/test_ndr_mission_contracts.py`: **19 passed**
- `test_ndr_queue_e2e_4_items`: failing at baseline, **now passes**
- The 18 remaining failures are pre-existing and unrelated: inventory_intelligence (10),
  ccc_layer gates (3, failing at HEAD on `OrderContext.order_value`), boundary_corrections (1),
  normalization_worker (2), openai_api (2).
- The openai_api pair moved from setup-ERROR to FAILED. Cause: fixing the `main.py` NameError
  (below) let those tests actually run, exposing a pre-existing AZM display-prefix assertion
  mismatch (`'🔸 ᴀᴢᴍ ┃ Mocked…' != 'Mocked…'`). Unrelated to NDR.

## Bug found in the uncommitted working tree

`src/main.py` had `logger` used in `lifespan`'s **shutdown** path but never defined — the
startup calls had been switched to `logging.info` while the shutdown ones were not. Every
shutdown raised `NameError`, so `ndr_poller.stop()`, `gateway.close()` and
`MongoDBManager.disconnect()` never ran. Fixed by binding `logger = logging.getLogger(__name__)`.

Fixing it exposed the next one, left unfixed as out of scope: `gateway.close()` raises
`AttributeError: 'LiteLLMGatewayAdapter' object has no attribute 'close'`. Note that
`gateway.connect()` is currently commented out in the same function, so the shutdown path is
closing a gateway that was never opened.

## Explicitly NOT done

- **`scripts/certify_gate2.py` is untouched.** The `DummyCCC` mock is still there. Removing it
  requires answering how a synthetically-seeded AWB hydrates through the CEM adapter/API path,
  which I could not answer without guessing at ShopDeck seeding. **Until that is resolved, that
  script's output must not be cited as evidence that context hydration works.**
- **No LLM behavioural harness** for scenarios A–M. The deterministic tier is what gates; the
  advisory tier remains to be written.
- **No physical call was made.**
- `DummyAction` remains in the poller's production dispatch path, still carrying a hardcoded
  `customer_phone: "1234567890"`. Pre-existing debt, deliberately not entrenched further.

## Gate 3 recommendation: NOT READY

The mission now provably reaches `session_constants`, and the greeting provably opens with the
reason and no date ask. That is real progress, and all of it is machine-verified.

But mission **retention** across turns is prompt adherence only — there is no server-side state
enforcement, and nothing in this change makes Priya's mid-call behaviour testable. Requirements
8, 9 and 10 are addressed by instruction text, and instruction text is not a guarantee.

Two things should be true before another physical call:
1. The scenario A–M harness runs against the real prompt configuration and passes.
2. The ShopDeck writeback is confirmed working end to end against a live endpoint — it has
   never once succeeded, so no NDR outcome from any prior call was ever persisted. Note that
   this means earlier physical-call evidence proves less than it appears to.
