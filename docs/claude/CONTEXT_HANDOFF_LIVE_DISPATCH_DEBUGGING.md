# Context handoff — live NDR dispatch debugging session

Written by: Claude
Date: 2026-09-08 (evening, after `CONTEXT_HANDOFF_FOR_NEW_GEMINI_AGENT.md`)
Why this exists: after the earlier Gate 3 dispatch audit was fixed and committed, the user ran
Brain against 5 genuinely real, live NDR events and had a real phone conversation with Priya on
one of them. This document is the full record of what that live test surfaced, what was fixed,
what is still uncommitted, and what is still open. Read this before touching NDR dispatch,
`ccc_builder`, `ndr_queue_poller.py`, or `exotel_webhooks.py`.

---

## 0. Sequence of events this session

1. Earlier today's Gate 3 dispatch audit was completed and committed (commits `0ba1d3b` through
   `11fb059` — see `TODO_GATE3_ROADMAP.md` and `CONTEXT_HANDOFF_FOR_NEW_GEMINI_AGENT.md` for that
   work).
2. Separately, Gemini fixed an `_os` typo in `sync_shopdeck_mcp_data.py` (commit `17db32d`) and,
   critically, also fixed the proxy engine to backfill `customer_info` for old AWBs (commit
   `20252df`). This second fix looks like the actual reason enrollment started working — see
   §4 for why the `_os` typo alone did not explain the observed symptoms.
3. ShopDeck's enrollment then fired 5 real NDR events. Brain's live local poller (running
   `--reload` on port 8000, continuously polling `api-shopdeck.aarambooks.cloud`) claimed and
   attempted to dispatch all 5. The user received a real call, talked to Priya, and reported
   getting a second call waiting while on the first.
4. Claude independently verified this in `~/AaramDevLauncher/brain_backend.log` and found real
   bugs — not the fluke it first looked like. Three were fixed and are live but **uncommitted**
   (§2). While reading back the actual call transcript from Mongo to verify the fixes, a fourth,
   more serious structural bug was found and also fixed (§3).

---

## 1. What actually happened to the 5 real NDR events

| AWB | Diagnosis | Result |
|---|---|---|
| 24899810618332 | CUSTOMER_UNAVAILABLE → seller_reattempt | Call connected — the one the user talked to |
| 24899810617024 | CUSTOMER_UNAVAILABLE → seller_reattempt | Call connected — the "second call waiting"; a genuinely separate real AWB, both routed to the test phone by `TEST_PHONE_OVERRIDE` |
| 24899810618844 | attempt=3 | Correctly suppressed, `POLICY_PROHIBITED` — the attempt-tiering policy from the earlier audit works |
| 14217131991594 | BUYER_REMORSE_OR_REJECTION → confirm_intent_to_receive | Failed to dispatch, retried 3×, identical error every time |
| 24899810615311 | BUYER_REMORSE_OR_REJECTION → confirm_intent_to_receive | Failed to dispatch, retried 2×, identical error every time |

## 2. Bugs found and fixed against the failed items (uncommitted)

**Bug A — `execution_intent` only ever set on one of four voice-dispatch strategies.**
`src/intelligence_domains/ndr/knowledge.py`, `determine_strategy()`. Only the Rule 5 branch
(`seller_reattempt`) set `execution_intent` on the `InterventionRecommendation`. Rules 2–4
(`courier_dispute`, `address_enrichment_request`, `confirm_intent_to_receive`) never did, but
`CustomerEngagementExecutor.prepare_engagement()` (`src/infrastructure/adapters/customer_engagement/executor.py:37`)
unconditionally requires it for any item the orchestrator marks `should_dispatch=True`. Any NDR
diagnosed as buyer-remorse, suspected-fake-attempt, or address-defect could never complete a
call, ever, no matter how many times it was retried — confirmed by the same AWB failing
identically 3 times over ~15 minutes in the log. **Fix:** added the same
`execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)`
to all three remaining branches. `concierge_escalate` (Rule 1) deliberately still does not get
one — that path never reaches the voice dispatcher (`should_dispatch` is always False when it
fires).

**Bug B — `UnboundLocalError` in ShopDeck's own failure-handling path, itself hidden by Bug A.**
`business_systems/shopdeck/backend/api/repositories/ndr_queue.py`, `apply_failure()`, the normal
(non-terminal) `else` branch:
```python
else:
    new_status = "failed_retryable" if new_status != "permanently_failed" else "permanently_failed"
    new_status = "failed_retryable"
    terminal_sql_part = ""
```
Line 1 references `new_status` before it is ever assigned in that branch, crashing with
`UnboundLocalError` on every normal `failed_retryable` transition — visible in the log as a 500
on `PATCH /api/v1/ndr/queue/{id}/status`. Combined with Bug A, this meant a permanently-broken
item (Bug A) could not even be marked failed (Bug B), so it just sat claimed until its lease
expired and got silently reclaimed and retried forever. **Fix:** deleted the dead first line;
the branch is now just `new_status = "failed_retryable"`. **This fix needs a VPS redeploy
(`mac_to_vps_deploy.sh` from the shopdeck repo) to take effect** — Brain only talks to the
deployed instance at `api-shopdeck.aarambooks.cloud`, never to local ShopDeck code.

**Bug C — the one successful call's outcome silently never reached ShopDeck.**
The call to AWB `24899810618332` succeeded, and the customer agreed to reschedule
(`CONFIRM_RESOLUTION` / `agreed` / `reschedule`). `src/api/webhooks/exotel_webhooks.py`'s
`submit_intelligence()` call then threw an exception with an **empty `str()`** — no
`POST .../intelligence_results` ever shows up in the log at all, suggesting a timeout or
cancellation rather than a clean HTTP error — and per the code's own safety design (already
correct — do not free a won claim and silently reopen the exact race it exists to close), it did
not retry. Net effect: the customer's real agreement was never recorded in ShopDeck. **Fix:**
wrapped the `submit_intelligence` call in a 3-attempt retry with backoff, and log
`type(err).__name__` + `repr(err)` (not just `str()`, which is exactly what printed blank here)
so a real failure is diagnosable next time. **Not yet done:** the specific lost outcome for AWB
`24899810618332` was never resubmitted — the exact payload is still sitting in the log
(`result_id=res_8b9be62e5896543289012cb3fe85511e`) if someone wants to replay it by hand.

## 3. Bug D — found while reading back the real transcript, more serious than A–C

The user asked Claude to read and analyze the actual transcript of the successful call. Reading
it back from Mongo (`aarambooks_ndr_communications.customer_engagement_events`, engagement
`eng_2725b5eeebbb505fbb27d11da6f97508`) surfaced something worse than a dispatch failure: **the
bot fabricated a product name.** It told the customer their order was a "Cotton Bedsheet" —
confirmed by the user not to exist anywhere in the catalog. It also said, verbatim, "मैंने
आपकी डिलीवरी दस सितंबर के लिए शेड्यूल कर दी है" ("I have scheduled your delivery for 10th
September") — a direct violation of `instruction_ndr`'s explicit rule against claiming an
execution has occurred, and Brain has no authority to schedule anything with the courier at all.

Root cause, confirmed by literally reproducing `build_session_constants()` against the real
stored engagement document: the `session_constants` payload actually sent to Exotel for this
call contained only `brand_name`, `engagement_id`, `action_request_id`, `awb_no`, and the ten
static instruction strings — **none** of the dynamic per-call context (product, price, offered
reattempt dates, pincode, prior communication history, mission fields) that the whole earlier
"give Priya the full NDR context" work (commit `9d94d95`) was supposed to deliver. The dynamic
greeting even fell back to its literal hardcoded default string ("delivery fail हो गई थी")
instead of the real failure reason — direct proof in the transcript itself that the context was
empty, not just incomplete.

The actual bug: `src/workers/ndr_queue_poller.py` built the CCC (`ccc_builder.build(action)`)
but never called `ccc_builder.project(ccc)`, and stored a bare
`{awb_no, customer_phone, queue_item_id}` dict as `call_context` instead of the projection.
`build_session_constants()` (`exotel_webhooks.py`) reads every dynamic fact out of
`engagement.call_context` by the flat key names defined on `CustomerConversationProjection` — so
with the projection never computed or stored, every one of those keys was always absent, on
every real call the live poller has ever dispatched, not just this one. `scripts/inspect_real_context.py`
(the one-off inspection script from earlier this session) already does this correctly
(`call_context=projection.model_dump()`) — the production poller was simply never brought in
line with it.

A second, related bug: `exotel_webhooks.py`'s reattempt-date matcher read
`offered_reattempt_date_1/2` from `ccc_snapshot` (the raw, nested CCC object saved on the
engagement, whose top-level keys are `ccc_id`/`target_identity`/`customer_profile`/`order_facts`/
`product_context`/`directive`) — those two fields only ever existed on the projection, never on
the raw CCC, so this lookup was guaranteed to return `None` regardless of what the customer said.
This is exactly why the real writeback payload for the successful call had `action_parameters: {}`
even though the customer explicitly agreed to "10th September, 10 AM" in the transcript.

**Fix, both uncommitted:**
- `src/workers/ndr_queue_poller.py`: now calls `ccc_builder.project(ccc)` and passes
  `{**projection.model_dump(), "queue_item_id": queue_item_id}` as `call_context` (queue_item_id
  has no home on the projection itself, so it's merged in separately — the writeback path needs
  it to identify which `ndr_queue` row to update).
- `src/api/webhooks/exotel_webhooks.py`: the reattempt-date matcher now reads
  `offered_reattempt_date_1/2` from `call_context_for_lookup` instead of `ccc_snapshot`.

**Not fixed, and not a Brain bug:** the bot's past-tense "I have scheduled it" claim is a
persona/LLM-adherence issue, not a wiring bug — `instruction_ndr` already explicitly forbids it.
Worth watching on the next real call now that context actually reaches the bot; if it recurs
with full context present, that's a prompt-strength problem in `bot_persona.txt` or the
underlying model, not something fixable in Brain's Python code.

## 4. Note on Gemini's two commits tonight

Commit `17db32d` ("Fix _os typo in sync engine") was independently verified by Claude at the
time and found **not** to explain the observed symptoms — 0 of the 10 specific backlogged real
AWBs were actually enrolled after that fix deployed, with the total `ndr_queue` row count
unchanged. Commit `20252df` ("Fix proxy engine to backfill `customer_info` for old AWBs"),
made shortly after, looks like the fix that actually mattered — it matches the alternative
hypothesis Claude raised at the time: `enroll_eligible_ndrs()`'s query INNER JOINs against
`customer_info` requiring a non-empty `customer_number`, so backfilled candidates without a
matching `customer_info` row could never enroll regardless of the `_os` typo. This has not been
independently re-verified against the database by Claude — flagging it here rather than treating
it as confirmed, consistent with this session's rule of not accepting a fix as proven until
checked against the real system.

## 5. Current uncommitted working-tree state

```
 M business_systems/shopdeck/backend/api/repositories/ndr_queue.py   (Bug B fix)
 M src/api/webhooks/exotel_webhooks.py                                (Bug C + Bug D fixes)
 M src/intelligence_domains/ndr/knowledge.py                          (Bug A fix)
 M src/workers/ndr_queue_poller.py                                    (Bug D fix)
?? scripts/inspect_real_context.py   (one-off inspection tool, not yet committed; safe to keep)
```
The ShopDeck-side fix (Bug B, `ndr_queue.py`) needs `mac_to_vps_deploy.sh` run from the shopdeck
repo before it takes effect in production — everything else is local Brain code, live
immediately via `--reload`.

## 6. Open items

- Resubmit or otherwise reconcile the lost outcome for AWB `24899810618332` (Bug C) — the
  customer's real agreement to reschedule to 10th Sept is not currently in ShopDeck.
- Deploy the ShopDeck-side `apply_failure` fix (Bug B) to the VPS.
- Commit today's evening fixes (Bugs A–D) once the user is ready.
- Watch the next real call closely: with Bug D fixed, Priya should receive real product/price/
  date/pincode/history context for the first time in production. If she still fabricates
  anything or still claims a past-tense execution, that points at the persona/model layer, not
  Brain's plumbing.
- Independently re-verify Gemini's `customer_info` backfill fix (§4) against the real database
  if a fresh backlog check is wanted.
