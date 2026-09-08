# Gate 3 writeback verification — implementation report

Author: Claude (implementation)
Date: 2026-09-08
Scope: took over execution from Gemini's drafted gate3_writeback plan after review found it
would not run as written; fixed the plan's errors, then found and fixed two further real
bugs that only a genuine end-to-end run against the live stack could surface.

## What was built

`scripts/certify_gate3_writeback.py` (new) - corrects the three factual errors from the
prior plan review (real route `/api/customer-engagement/voice/exotel/transcript`, real
tables `ndr_intelligence_results` / `ndr_queue.queue_status='action_ready'`, and an actual
claim step via `process_next_item()` so `ndr_queue.claimed_by` is genuinely set before the
writeback is attempted). It fires three transcript turns at one real engagement - UNCLEAR,
then a decisive refusal, then a DIFFERENT decisive resolution - specifically to prove the
one-per-engagement guard works, not just that identical-payload retries are idempotent
(which was already trivially true and wouldn't have caught the real risk).

`src/infrastructure/adapters/customer_engagement/repository.py:claim_intelligence_writeback` -
an atomic Mongo compare-and-swap that lets exactly one transcript turn per engagement win the
right to call ShopDeck. This exists because `persist_intelligence_atomic`
(`business_systems/shopdeck/backend/api/repositories/ndr_queue.py:505-559`) allows only ONE
`ndr_intelligence_results` row per `engagement_id`, ever - not per `result_id`. Since Exotel's
transcript webhook fires once per turn, without this guard an early ambiguous turn could
consume the one allowed slot and a customer's real, later, decisive answer would be silently
dropped when ShopDeck rejected the second write. `handle_transcript` now also skips the
writeback attempt entirely for `UNCLEAR` classifications, so an ambiguous turn never even
competes for the slot.

`src/infrastructure/adapters/shopdeck_cem_adapter.py:_authed_request` - centralizes the
401-detect-clear-cache-retry pattern that previously existed only on the read path
(`execute_evidence_request`). `claim_ndr_work`, `register_engagement`, `update_queue_status`,
and `submit_intelligence` - the entire write surface - had no such handling; in the Brain's
long-running process, one stale M2M token would have failed every write until restart.
Dispatches via `client.post`/`client.patch` (not `client.request`) specifically so existing
tests that patch `httpx.AsyncClient.post`/`.patch` directly keep working.

## Two real bugs found only by running against the live stack, not by review or unit tests

**`queue_item_id` was never actually stored on the engagement, and the fallback silently
posted the wrong value to ShopDeck on every real writeback.** `handle_transcript` read
`engagement.get("metadata", {}).get("queue_item_id")` - but `CustomerEngagementRecord`
(`src/infrastructure/adapters/customer_engagement/models.py:37-56`) has no `metadata` field
at all, so that lookup always returned `None`. The fallback,
`queue_item_id, _ = parse_correlation_metadata(payload)`, was wrong on its face:
`parse_correlation_metadata` returns `(engagement_id, action_request_id)`, not a queue item
id - so every real writeback attempt posted the **engagement_id** to ShopDeck in the
`queue_item_id` field. The first live run of `certify_gate3_writeback.py` caught this
immediately: ShopDeck 500'd because the row it tried to `SELECT ... FOR UPDATE` under that
id didn't exist. No unit test caught it because every one of them supplied `queue_item_id`
directly via a mocked dict, matching the code's own wrong assumption rather than the real
shape of a `CustomerEngagementRecord`.

Fixed by actually storing `queue_item_id` where the poller already has it -
`src/workers/ndr_queue_poller.py`'s `call_context` dict, passed to `prepare_engagement()` -
and reading it back from `engagement["call_context"]["queue_item_id"]` in the webhook. Three
test fixtures that mocked the old (never-real) shape
(`tests/test_ndr_queue_e2e_local.py`, two call sites) were updated to match.

**The `sa:<client_id>` claimer identity does match ShopDeck's JWT `sub` claim** - confirmed
empirically, not just inferred: the live run's `claimed_by` came back as exactly
`sa:sa-aaram_brain-225eca38`, matching the poller's `claimer_id`
(`src/main.py:271`), and `persist_intelligence_atomic`'s ownership check passed. This was an
open question in the prior review (item 6) that could only be settled by a real end-to-end
run; it now has a definitive, verified answer.

## Live verification result

```
Turn 1 (UNCLEAR)                 -> writeback deferred, no ShopDeck call attempted
Turn 2 (decisive refusal)        -> claimed the slot, POST /intelligence_results -> 201 Created
Turn 3 (different resolution,
        same engagement)         -> writeback deferred (slot already claimed), NO second POST
ndr_intelligence_results rows for this engagement: 1 (not 2, not 0)
ndr_queue.queue_status:          action_ready (exact string, confirmed against real repository code)
```

PASS. This is the first time this writeback path has been proven to work end to end against
the real ShopDeck deployment - every prior version of it (the original `dummy_token`, the
`settings.shopdeck_token` version, and the schema-mismatched original payload) would have
failed had it ever been exercised for real; none of them ever were until this session.

## Test evidence

Full suite (excluding the LLM harness and two files broken by a pre-existing, unrelated
`pymongo`/`mongomock_motor` import collision): 18 failed, 404 passed - identical failing
tests by name to the established baseline. Nothing in this round's fixes introduced a new
deterministic failure.

## What's still open

- The shared remote queue backlog is now 8 eligible items (down from 10 earlier this session -
  more stale items hit their claim-attempt limit during this round's real claims). Still
  trending in the wrong direction over time without a deliberate cleanup; that's still your
  call, not something I've done unilaterally.
- `settings.shopdeck_token` (the setting that was never actually used, now dead) could be
  removed from `src/shared/config.py` - left in place since removing unused config is a
  separate, lower-stakes cleanup from anything asked this session.
- Everything already listed as open in the prior two reports: no server-side conversation
  state enforcement in V1, the LLM behavioral harness result (12/13) is advisory not gating,
  and no physical call has been made.
