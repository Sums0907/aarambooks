# Senior Review — NDR Conversation Mission/State Contract implementation plan

Reviewer: Claude (senior engineering review)
Date: 2026-09-08
Subject: Gemini's proposed implementation plan for the NDR Conversation Mission/State Contract

**Verdict: direction is right, do not approve as written.** The plan contains one architectural
contradiction, one ordering bug, and one silent-failure path that would let it report success while
the mission never reaches Priya.

## What it gets right

Mission lives on `ConversationalDirective` in `src/brain_core/action_engine/contracts.py` — correct box.
No generic workflow engine. Flow direction (Brain -> CCC -> projection -> `session_constants`) matches
the existing pipeline. Refuses to place a real call.

## Five things to fix before execution

### 1. `current_state` cannot live in a frozen snapshot

`ConversationalDirective` is `frozen=True`, and `CustomerConversationContext` is documented as an
"Immutable call-scoped authoritative snapshot". `current_state` changes by definition. As planned,
`current_state` is only ever the *initial* state — the plan never says who owns transitions across
turns, or where they persist.

This matters because the only per-turn hook is `handle_transcript`
(`src/api/webhooks/exotel_webhooks.py:395`), **which the plan does not touch**, and which today does
crude keyword matching (`"tomorrow" in transcript -> RESCHEDULE`) and returns `data: {}` — it cannot
steer the live call. So requirement 10 ("mission survives interruptions") is not actually implemented
by this plan; it is delegated to the LLM honoring prompt text.

That is a defensible V1 — but it must be stated, not glossed. The plan's phrase "guaranteeing that
Priya receives the mission parameters at initialization" is doing a lot of work, and requirement 13
specifically warns against pretending session variables are system-level guarantees.

Required: mission fields immutable in the directive; `current_state` either dropped from V1 or
explicitly renamed `initial_state`; and a written admission in the final report that V1 has no
server-side state transitions.

### 2. Ordering bug — the mission is built from data the poller does not have yet

The plan says construct the mission from `ndr_reason_at_enroll` and `past_delivery_attempts`. But
`past_delivery_attempts` is hydrated *inside* `ccc_builder.build()` from `evidence.get("ndr_count")`
(`src/brain_core/context_engine/ccc_builder.py:72`) — and the directive is an **input** to `build()`,
constructed at `src/workers/ndr_queue_poller.py:112` before hydration runs. This is circular.

The fix is available: the claimed queue `item` already carries `ndr_reason_at_enroll` and
`ndr_count_at_enroll`. Mission must be sourced from the queue item, not from post-hydration CCC.
State this explicitly in the plan or it will be improvised at execution time.

Related: building the mission inside `DummyAction` in the worker puts NDR domain intelligence in
`src/workers/`, not `src/intelligence_domains/ndr/`. Requirement 2 assigns mission interpretation to
Brain/NDR-ID. The mission factory belongs in the NDR domain; the poller should call it.

### 3. Silent-failure path — the webhook allow-list

`src/api/webhooks/exotel_webhooks.py:330-337` copies context into `session_constants` via a
**hardcoded key list**. Add mission fields to the projection but forget this list, and the mission
silently never reaches Priya — while every test that asserts on the projection still passes. This is
the single most likely way the change ships broken.

Also: the plan says "add `mission_details` dictionary **or** specific fields." That ambiguity is the
difference between working and broken. `CustomerConversationProjection` is `extra='forbid'` with flat
scalars, and the loop does `str(value)` — a nested dict becomes a Python-repr blob
(`"{'conversation_mission': 'NDR_RECOVERY', ...}"`) inside the prompt.

Required: flat scalar mission fields on the projection, the webhook allow-list extended with each new
key, and a test asserting the literal `session_constants` payload contains every mission key.

### 4. `generate_dynamic_greeting` is a rewrite, not a "refine"

The current function (`src/api/webhooks/exotel_webhooks.py:151-206`) ends *every* greeting with
"Are you available to receive your order tomorrow?" — exactly the pushy opening requirement 9 bans,
and the opposite of requirement 5's target close ("क्या अभी बात करना सुविधाजनक है?").

Three further problems the plan does not see:
- it is English, while the spec opening is Hindi;
- it infers facts by string-matching prompt text (`"courier" in c.lower()`);
- it uses `random.choice`, making the opening non-deterministic, so requirement 11's assertions
  cannot be written against it.

Deterministic rendering from `why_this_call` is a prerequisite for the tests, not a nicety.

### 5. The test strategy cannot produce the evidence requirement 14 asks for

LLM-simulated scenarios A-M are non-deterministic — a green run proves nothing repeatable. Split into:

- **Deterministic gating tier:** given a queue item + CCC, assert the exact `session_constants`
  contents, assert the greeting contains the failure reason and contains no reschedule ask, assert
  absent facts never render. This tier gates the change.
- **Non-blocking LLM behavioral harness** for scenarios A-M, clearly labelled as advisory.

The regression claim (requirement 12) is currently unbackable: `scripts/certify_gate2.py` in the
working tree **mocks `ccc_builder.build` to return an empty `DummyCCC`**. Regressions run through that
path structurally cannot detect a mission that fails to hydrate — the exact thing being built. That
mock must be removed before the script is cited as evidence.

## Three requirements the plan silently skips

- **Req 7** ("never claim I checked unless a lookup occurred") — no corresponding `instruction_*`
  session constant is added.
- **Req 3** — the nine states are planned as free-form `str` / `list[str]`. Make them a `StrEnum` so
  an invalid state is a validation error rather than a typo that reaches Priya.
- **Terminal outcomes** — `CUSTOMER_UNAVAILABLE`, `CUSTOMER_REFUSED`, `COMPLETED` must map back to
  ShopDeck queue status at session-end. The plan is silent on outcome writeback.

## Bottom line

Send the plan back with items 1-5 as required amendments. As written it would likely produce a change
that looks complete, passes its own tests, and never actually delivers the mission into the call.
