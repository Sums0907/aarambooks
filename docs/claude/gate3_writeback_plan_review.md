# Senior Review — Gemini's `certify_gate3_writeback.py` plan, code + identity gotchas

Reviewer: Claude
Date: 2026-09-08
Subject: the currently drafted implementation_plan.md ("Perform a synthetic runtime
integration test to verify the terminal writeback pathway...")

**Verdict: do not execute as written.** Three concrete factual errors (route path, table
names, missing claim step) plus one structural design gap in code I delivered in the prior
round - the gap is more consequential than anything in this specific plan, and this plan's
own test won't catch it.

## Factual errors in the plan (checked against actual code, not inferred)

**1. Wrong webhook route.** The plan invokes `/api/webhooks/exotel/transcript`. The real
registered prefix is `/api/customer-engagement/voice/exotel`
(`src/api/webhooks/exotel_webhooks.py:15`) - the actual path is
`/api/customer-engagement/voice/exotel/transcript`, matching what `certify_gate2.py` already
uses for `/session-start`. As written this 404s immediately.

**2. Wrong table names for persistence verification.** The plan says check
"`ndr_queue.queue_status` and `ndr_action_history` (or similar tables)." Reading
`persist_intelligence_atomic` directly
(`business_systems/shopdeck/backend/api/repositories/ndr_queue.py:505-559`):

- It writes to **`ndr_intelligence_results`**, not `ndr_action_history` - that table doesn't
  get touched by this code path at all. (`ndr_action_log` is a real table, but it's for a
  different history stream and unrelated to this write.)
- It sets `ndr_queue.queue_status = 'action_ready'` specifically - not a generic "updated" or
  a status matching the mission's `NDRConversationState` terminal names. Assert the exact
  string, not "some update happened."

This is the same category of error as the `shipments`/`shipment_items`/`customers` guess
from the prior plan round - table names invented from what sounds plausible, not read from
the code that actually runs. Read the repository before writing the verification query.

**3. Missing claim step - and this one will make the test fail outright.**
`persist_intelligence_atomic` does this ownership check before writing anything
(line 518-519):

```python
if row["claimed_by"] != claimer_id:
    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")
```

The plan's step 1 seeds the queue item "in the exact same manner as `certify_gate2.py`" -
which inserts it directly with `queue_status = 'eligible'`, leaving `claimed_by` NULL. Step 2
says "programmatically trigger the NDRQueuePoller claim process," which is the right idea,
but the plan needs to say explicitly that this claim MUST go through the real
`shopdeck_adapter.claim_ndr_work()` call (which sets `claimed_by` server-side) - a raw SQL
seed alone will leave the row unclaimed, and the writeback step will 403 with
`PermissionError` unconditionally, regardless of anything else the test does correctly.

## Identity/auth gotchas

**4. No token-refresh retry on the write path.** `_get_shopdeck_token()`
(`shopdeck_cem_adapter.py:21-38`) caches the M2M token in a module-level global with no
expiry check. Only `execute_evidence_request` (the READ path) has 401-detect-and-retry logic
(`shopdeck_cem_adapter.py:183`: "Token may have expired — clear cache and retry once").
`claim_ndr_work`, `register_engagement`, `update_queue_status`, and `submit_intelligence` -
the entire WRITE path, which is what both this plan and the webhook's writeback (item 2 from
the prior round) depend on - have no such retry. In a long-running process (the Brain's
uvicorn process has been up since 4:03AM today), a token that expires mid-session will cause
every subsequent write to fail with an unhandled 401 until the process restarts. Worth fixing
independent of this specific plan - the same retry-and-clear-cache pattern already proven on
the read path should be added to the write methods, or centralized in `_get_auth_header()`
so every caller gets it for free.

**5. Don't log the bearer token.** The plan's verification report wants to capture
"Auth headers used." The actual header is a real, valid M2M bearer token
(`shopdeck_cem_adapter.py:60`, `Authorization: Bearer <token>`) that authenticates as the
Brain's service identity against production ShopDeck. If this report gets committed the way
prior session logs and certification reports have been (`docs/ag_chat_*.md`, this pattern is
established in this repo), that's a live credential in git history. Log token *presence* and
which client_id was used, never the token value.

**6. `claimer_id` / JWT `sub` matching is a real but pre-existing correctness dependency,
not a bug - confirm it once, don't assume it.** The poller's `claimer_id` is
`f"sa:{settings.brain_client_id}"` (`src/main.py:271`), and `persist_intelligence_atomic`
compares it against `user.get("sub")` from the decoded M2M JWT (ShopDeck's `auth.py`). These
are deliberately paired (the `sa:` prefix convention looks intentional), but I can't verify
the identity server's exact `sub` claim format from this repo - it's a separate service. This
plan is actually a reasonable way to confirm that pairing empirically for the first time, as
long as item 3 above is fixed so the ownership check is even exercised correctly.

## A larger gap this plan's own test won't catch

`persist_intelligence_atomic` enforces **one intelligence result per engagement, ever**
(line 534-536):

```python
existing_by_eng = await conn.fetchrow("SELECT * FROM ndr_intelligence_results WHERE engagement_id = $1", ...)
if existing_by_eng:
    raise ValueError(f"engagement_already_has_result")
```

This is stricter than result_id-based idempotency (which only catches identical retries).
The writeback code from the prior round (`src/api/webhooks/exotel_webhooks.py`,
`handle_transcript`) derives `result_id` per-turn from
`uuid5(engagement_id + conversation_state)` and is invoked on every transcript event -
Exotel's transcript webhook fires per-turn over the course of a call, not once at the end
(the whole codebase already treats it this way: `EventId`, `"transcript_events"` in the
session-start webhook config). That means **only the first turn that produces any classified
state ever gets persisted.** If a customer's real, final answer ("cancel it") arrives after
an earlier ambiguous turn ("UNCLEAR") already wrote a result, the second write throws
`ValueError("engagement_already_has_result")`, is caught by the handler's blanket
`except Exception: logger.error(...)`, and is silently dropped - ShopDeck ends up recording
the WRONG or a premature outcome for the call, with no visible error anywhere except a log
line.

The plan's own idempotency check (step 6, "re-fire the same webhook payload") won't surface
this - re-sending an identical payload only re-exercises the result_id path, which already
works correctly. Catching this needs a *different* payload on a *second, distinct* transcript
event for the same engagement, asserting that ShopDeck's response reflects the update (or, if
it can't, that the design deliberately treats the first-classified-turn as final and that's
accepted behavior, which would then need to be a stated decision rather than an accidental
one).

## Recommendation

Fix 1-3 before running anything (route, table names, actual claim step). Decide 4 and 5
regardless of this specific plan - they're standing production risk. The engagement-result
gap is the one item here I'd treat as blocking for Gate 3 specifically: right now, a real
multi-turn NDR call has a real chance of writing back the wrong outcome, and nothing in the
current test surfaces that.
