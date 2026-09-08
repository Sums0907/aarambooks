# Senior Review Round 2 — NDR Conversation Mission/State Contract (revised plan)

Reviewer: Claude (senior engineering review)
Date: 2026-09-08
Subject: Gemini's revised implementation plan, after round-1 review

**Verdict: substantially improved. Approve to execute after three blocking corrections, plus two
questions that must be answered before the work starts rather than discovered mid-execution.**

## Round-1 items: resolved

| # | Round-1 finding | Status |
|---|---|---|
| 1 | `current_state` in a frozen snapshot | Fixed — renamed `initial_state`, V1 limitation stated explicitly |
| 2 | Mission built from un-hydrated data | Fixed — dedicated `mission_factory` in `src/intelligence_domains/ndr/`, sourced from queue item, runs before `ccc_builder.build()` |
| 3 | Webhook allow-list silent failure | Fixed — flat scalar fields, allow-list extension called out by line number |
| 4 | Greeting is a rewrite | Fixed — deterministic, Hindi, no reschedule ask |
| 5 | Test strategy | Fixed — deterministic gating tier + advisory LLM tier, `DummyCCC` mock removal |

The three silently-skipped requirements (lookup-claim instruction, `StrEnum` states, terminal outcome
writeback) are now all in scope.

## BLOCKING — three corrections required

### B1. The state enum silently drops `RETURN_TO_NDR` and renames four spec'd states

Requirement 3 named exactly nine V1 states:

```
INTRODUCE_REASON, CUSTOMER_RESPONSE, ANSWER_CUSTOMER_QUESTION, RETURN_TO_NDR,
CONFIRM_RESOLUTION, CUSTOMER_UNAVAILABLE, CUSTOMER_REFUSED, UNCLEAR, COMPLETED
```

The plan proposes eight:

```
INTRODUCE_REASON, CONVERSING, ANSWERING_QUESTION, RESOLVING,
COMPLETED, CUSTOMER_UNAVAILABLE, CUSTOMER_REFUSED, UNCLEAR
```

Three renames (`CUSTOMER_RESPONSE`→`CONVERSING`, `ANSWER_CUSTOMER_QUESTION`→`ANSWERING_QUESTION`,
`CONFIRM_RESOLUTION`→`RESOLVING`) and **one deletion: `RETURN_TO_NDR` is gone.**

`RETURN_TO_NDR` is the single most load-bearing state in the entire request. Requirements 8 and 10 are
*precisely* "after answering a side question, acknowledge, retain the mission, and naturally continue
toward NDR resolution." Deleting the state that names that behavior, while keeping `return_to_mission`
as a free-text prose string, leaves the core behavior with no representation in the contract at all.

Required: restore the nine spec'd state names verbatim. If Gemini believes a different taxonomy is
better, that is a proposal to raise explicitly, not a silent rename of an approved contract.

### B2. `allowed_next_states` was dropped from the mission contract

Requirement 1 lists it explicitly. It is absent from the proposed `ConversationMissionContract`.

Given correction 1 (no server-side transition engine in V1), the field arguably carries no runtime
force — but that is an argument to be made and signed off, not a field to quietly vanish. Either
include it as prompt-level guidance, or state in the plan: "omitted because V1 has no transition
engine, per correction 1" and get explicit approval. Same class of error as B1.

### B3. `allowed_actions` now exists in two places and collides in the projection

`ConversationalDirective.allowed_actions` already exists
(`src/brain_core/action_engine/contracts.py`), is projected as `allowed_actions` in
`CustomerConversationProjection`, and already flows into `session_constants` via the allow-list loop.

The plan adds `ConversationMissionContract.allowed_actions`. Two identically-named fields on two
objects, both reaching the LLM prompt, with no statement of which is authoritative — plus a projection
key collision (`allowed_actions` vs `mission_allowed_actions`).

Required: pick one owner. Recommend the mission owns it and the directive's field is populated from
the mission, so exactly one key reaches `session_constants`.

## Answer these before starting, not mid-execution

### Q1. How does `certify_gate2.py` hydrate a synthetic AWB once the mock is removed?

The plan commits to removing the `DummyCCC` mock so the script exercises real hydration. Good — but
that mock exists because a synthetic seeded AWB 404s against the real ShopDeck API. The script seeds
`shipment_ndr_reports` and `ndr_queue` directly in Postgres, while `ccc_builder.build()` resolves
through the CEM adapter/API path, not those tables directly.

So removing the mock, as written, most likely just moves the failure. Decide up front: seed enough
ShopDeck state that the API path actually resolves, or certify against a real AWB. If neither is
possible, say so — but then Gate-2 regression evidence cannot claim to cover hydration.

### Q2. The transcript writeback this change builds on is currently non-functional

The plan adds terminal-outcome mapping (`CUSTOMER_UNAVAILABLE` / `CUSTOMER_REFUSED` / `COMPLETED`) to
`handle_transcript`. That handler's existing ShopDeck writeback has three defects it will inherit:

1. **`m2m_token = "dummy_token"`** — hardcoded (`src/api/webhooks/exotel_webhooks.py`, in the
   `httpx` block). Every writeback presumably fails auth today.
2. **`except Exception` around the whole writeback, with only a `print`** — so that failure is
   invisible. Tests will pass; production will do nothing.
3. **`queue_item_id` falls back to the string `"unknown"`** and posts anyway.

Adding terminal-outcome mapping on top of a path that never succeeds produces a change that is
unverifiable by construction. Fix the token and make the failure loud (raise, or at minimum log at
error with the response body) as part of this work, or explicitly descope terminal outcomes to a
follow-up.

### Bonus defect found while reviewing this path

The intent heuristic in `handle_transcript` uses **substring** matching:

```python
elif any(w in raw_transcript.lower() for w in ["cancel", "no", "don't want"]):
    intent = "RTO_CONFIRMED"
```

`"no"` as a substring matches `know`, `now`, `north`, `nothing`, `announce` — and this runs on
Hindi-English mixed transcripts. Any customer saying "now" or "I know" is currently classified as
**RTO_CONFIRMED (cancel the order)**. This is a live misclassification bug that this change makes
load-bearing. Fix it to word-boundary matching at minimum, ideally route it through the real
`reply_parser` the code comment already gestures at.

## Non-blocking notes

- **Deterministic tier must start from a queue item, not a hand-built projection.** If the test
  constructs a `CustomerConversationProjection` by hand and asserts on it, it will not catch a
  regression of the round-1 ordering bug. Start the test at `mission_factory(queue_item)` and assert
  all the way through `project()` into the `session_constants` payload.
- **Language mixing.** The greeting becomes Hindi while `session_constants` instructions and
  `objective` / `context_summary` remain English, and `customer_name` / `product_name` interpolate
  into a Hindi sentence. Acceptable, but decide it deliberately rather than by accident.
- **`DummyAction` survives this change.** It remains test scaffolding in the production dispatch path
  (`src/workers/ndr_queue_poller.py`), still carrying a hardcoded `customer_phone: "1234567890"`.
  Not this change's job to fix, but it should not be entrenched further, and it stays on the debt list
  ahead of any Gate 3 claim.

## Recommendation

Apply B1, B2, B3; answer Q1 and Q2 in the plan text. Then execute.

Gate 3 readiness remains a separate judgement — nothing in this plan produces server-side state
enforcement, so mission retention will be prompt-adherence only. That must be stated as a limitation
in the final report, not discovered on a live call.
