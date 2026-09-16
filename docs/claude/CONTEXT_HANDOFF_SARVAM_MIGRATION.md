# Context handoff — Exotel → Sarvam voice-bot migration

Written by: Claude
Originally written: 2026-09-11. Updated 2026-09-13 (twice), 2026-09-14 (twice), 2026-09-15,
2026-09-16 (twice) - Sarvam is no longer "mid-migration, blocked on missing details." Real
customers are being called autonomously and their outcomes are reaching ShopDeck's
`ndr_intelligence_results` correctly (verified 2026-09-16 against real transcripts and real
DB rows, not just logs). The newest work is a call-recording capture pipeline (Sarvam → R2 →
ShopDeck's `ndr_engagements.recording_url`) which itself needed a same-day reliability fix -
see bugs 11-12 and the dedicated section below. Read the TL;DR first if you're picking this
up fresh - it has the current, accurate state. The sections after it are the original build
history.

## TL;DR (current, as of 2026-09-16)

- **`TEST_PHONE_OVERRIDE` was removed from the VPS on 2026-09-14 - but a real bug meant
  ZERO real customers were actually reached until this was fixed on 2026-09-15.** Every
  single real dispatch attempt on 2026-09-15 (26 permanently_failed) failed with the exact
  same Sarvam 422 "Invalid phone number format" error seen with the test number the day
  before - except this time on real customer numbers. Root cause: ShopDeck's
  `customer_number` is stored as a plain 10-digit Indian local number, passed through with
  zero formatting; the 2026-09-14 phone-format fix only corrected the manually-set
  `TEST_PHONE_OVERRIDE` value, nobody had fixed the actual real-customer phone hydration
  path. Fixed 2026-09-15 in `src/shared/phone_format.py`
  (`to_e164_india`), applied in `sarvam_adapter.py` right before dispatch, deployed to the
  VPS and confirmed live. See bug 9 below for full detail. As of this fix, the poller is
  correctly configured to call real customers live within the calling-hours window, fully
  autonomously, with no human review step - but this had not actually happened successfully
  even once before this fix, despite the override being removed a full day earlier. Don't
  trust "override removed" as proof real calls are working - check actual dispatch outcomes.
- This was still a deliberate, explicitly-confirmed user decision, made *despite* two known
  open risks at the time: (1) nobody had yet reviewed the actual transcripts/quality of the
  real calls that completed on 2026-09-14 (now done - see
  `SARVAM_CALL_QUALITY_REVIEW_2026-09-14.md`, several real findings), and (2) production
  calls are running on the condensed test-version system prompt, not the full 835-line
  persona (`docs/voicebot/bot_persona.txt`) - still open. Local `.env` still has
  `TEST_PHONE_OVERRIDE` set (deliberately left alone - no poller runs locally).

- **Sarvam is live in production**, not a draft. `DEFAULT_VOICE_PROVIDER=SARVAM` is set on
  the VPS - real NDR dispatches go through Sarvam automatically via the normal poller, no
  manual script needed. `sarvam_app_version=25` is the real, user-confirmed committed value
  (bumped from `23` on 2026-09-15 as the agent's own published version moved forward on
  Sarvam's side; no longer the draft `4` described further down this doc).
- **The calling-hours window is currently 11 AM-9 PM IST on the VPS**, not the 7 PM repo
  default - `NDR_CALLING_HOURS_END_IST=21` is a deliberate `.env`-only override left in place
  for live testing (the setting only supports whole hours, so 21 rather than 20:30). Unlike
  the earlier 2026-09-14 `=23` override, this one has not been reverted as of 2026-09-16 -
  check the VPS `.env` directly before assuming either value.
- **Two more real production bugs found and fixed 2026-09-15/16** on top of the nine below
  (see bugs 10-11): an `engagement_registered` queue-status race that mis-tracked real
  dispatches, and a boolean-vs-string comparison bug that silently dropped
  `new_address_details`/`new_phone_number` from every single real call since the feature was
  written, undetected by the existing tests because they used the documented string form
  while every real Sarvam payload actually sends a JSON boolean.
- **A call-recording capture pipeline was built 2026-09-16** (Sarvam recordings → Cloudflare
  R2 → ShopDeck's `ndr_engagements.recording_url`, for the courier partner's priority
  escalation process) - and needed its own same-day reliability fix once tested against real
  live traffic (bug 12). See "Call recording capture pipeline" section below for full detail,
  including a real ShopDeck-side quirk this fix depends on. **The fix (bug 12) is committed
  but not yet deployed to the VPS as of this writing** - the live webhook path is still
  running the version that fails silently on every call; don't assume recordings are being
  captured in production until this is confirmed deployed.
- **Exotel still exists and still works** (nothing about it was removed), but it is no longer
  the default - `default_voice_provider` is a real config value now
  (`src/shared/config.py`/`executor.py`), not a hardcoded constant, specifically so this can
  be flipped without a code change again in the future.
- **The poller now enforces a real calling-hours window (11 AM-7 PM IST by default,
  `NDR_CALLING_HOURS_START_IST`/`NDR_CALLING_HOURS_END_IST`)** - added 2026-09-13 after
  realizing nothing previously stopped a real customer being called at 2 AM the moment an
  NDR became eligible; start moved from 9 AM to 11 AM later the same day per business
  decision. Checked before the poller ever claims a queue item, not after - an item outside
  the window is left completely untouched in ShopDeck's queue, not claimed and given back
  (which would burn into the limited `max_retries` budget). This means: **a real Sarvam test
  call will now only ever be placed between 11 AM and 7 PM IST**, regardless of when ShopDeck
  actually enrolls a fresh eligible item - don't be surprised if nothing happens outside those
  hours, that's the gate working correctly, not a stall.
- **Real end-to-end Sarvam calls have now completed, verified in the live logs (2026-09-14).**
  Once the NDR ingestion pipeline caught up and a backlog of eligible items appeared, the VPS
  poller claimed and dispatched them one at a time: `TEST MODE: Overriding customer phone to
  +918168583367` (this line is historical - `TEST_PHONE_OVERRIDE` has since been removed from
  the VPS, see the TL;DR above; a fresh log excerpt taken now would show the real customer's
  number instead) → Sarvam `200 OK` → the `call-completed` webhook fired → engagement flipped
  to `COMPLETED` (or `FAILED` for a `busy` outcome, which also correctly freed the dispatch
  slot) → `OutboundWritebackWorker` claimed and pushed the result back to ShopDeck. Four calls
  went out this way in one run, none overlapping.
- **Nine real bugs were found and fixed since this doc was first written** - see "Bugs found
  and fixed" below - a name-corruption bug, a missing per-call instruction variable, the
  `default_voice_provider` gap, the missing calling-hours gate, a retry-idempotency bug that
  was silently killing NDRs after their first failure, a wrong `TEST_PHONE_OVERRIDE` format,
  missing sequential-dispatch gating, and (the most recent, most impactful) real customer
  phone numbers being rejected by Sarvam for the exact same E.164 reason - the fix for the
  test number never touched the real-customer code path, so real dispatches kept failing for
  a full day after the test override was removed.
- **The dispatch pipeline now waits for a call to actually end before dispatching the next
  one** - added 2026-09-14 (`NDRQueuePoller._wait_for_call_completion`), because
  `max_concurrent_calls=1` alone only bounded how many claim/dispatch *pipelines* ran at
  once; it released its slot the instant a call was dispatched, not when it finished. With a
  backlog of eligible NDRs this could have fired several real calls back-to-back onto the
  same test number. Now the poller polls the engagement's status until Exotel/Sarvam's
  webhook marks it terminal (`COMPLETED`/`FAILED`/`ESCALATED`), bounded by
  `NDR_CALL_COMPLETION_MAX_WAIT_SECONDS` (default 600s) so a missed webhook can't hang the
  poller forever. Verified live: exactly one claim in flight at a time, confirmed via logs.
- **One thing to keep in mind, not a bug**: ShopDeck's `ndr_queue.queue_status` goes back to
  `action_ready` after a call completes (rather than something like `call_completed`), which
  reads as if the item became claimable again. It isn't - `claimed_by` stays set, so
  ShopDeck's own atomic claim won't re-select it. Likely `action_ready` is being reused to
  mean "reattempt window open," not "available to claim." Worth clarifying with the ShopDeck
  side if this ever needs to be told apart programmatically, but it isn't causing duplicate
  calls today.
- **Do not run more manual one-off test scripts for this.** The VPS's own poller is already
  correctly configured, running continuously, and has now proven it works end to end.

## Why this exists (origin of the migration)

User wants to move off Exotel because Sarvam is considered better. This is a live,
production-serving pipeline (NDR recovery calls to real customers) - nothing here is
theoretical or a greenfield build. The standing rule for this whole effort: verify against
real behavior, never trust documentation or a "should work" as sufficient - this handoff
tries to be explicit everywhere about what's actually confirmed vs. best-effort.

## What's built and verified

### 1. Provider abstraction (outbound dispatch)
- `src/infrastructure/adapters/customer_engagement/voicebot_adapter.py` (new) - a structural
  `VoiceBotAdapter` Protocol (`provider_name` + `dispatch_call()`). Any adapter with those
  two conforms automatically, no inheritance required.
- `ExotelVoiceBotAdapter` (`exotel_adapter.py`) got one additive line: `provider_name =
  "EXOTEL"`.
- `ExecutionIntent` (`src/brain_core/action_engine/contracts.py`) got one new optional
  field: `voice_provider: Optional[str] = None`. Defaults preserve current behavior for
  every existing caller.
- `CustomerEngagementExecutor` (`executor.py`) now holds `self.adapters: Dict[str, Any]`
  instead of a hardcoded `exotel_adapter` field, looked up by `engagement.provider` at
  dispatch time. The old `exotel_adapter=` constructor kwarg still works unchanged (registers
  under `"EXOTEL"`) - `src/main.py`'s wiring and all existing executor tests needed zero
  changes.
- **To add a real second provider**: write `SarvamVoiceBotAdapter` with `provider_name =
  "SARVAM"` and `dispatch_call()`, register it into the executor's `adapters` dict in
  `src/main.py`, set `voice_provider="SARVAM"` on whichever `ExecutionIntent`s should route
  there. No other file changes needed.

### 2. Shared, provider-agnostic core (inbound + writeback)
- `src/infrastructure/adapters/customer_engagement/context_variables.py` (new) -
  `build_provider_call_variables()`, the single allow-list of fields that reach any voice
  provider. Extracted so a field added for one provider can't silently miss the other (this
  is exactly the kind of gap that caused `bot_persona.txt`'s `instruction_payment` to go
  missing earlier - one list now, not one per provider).
- `src/intelligence_domains/ndr/reply_parser.py` gained:
  - `record_ndr_outcome_from_transcript()` - the transcript-classification-and-recording
    logic extracted out of Exotel's `handle_transcript()`. Exotel-only in practice today
    (Sarvam doesn't need it - see below) but available if a future provider also streams raw
    transcript turns.
  - `enqueue_ndr_intelligence_result()` - the CAS-claim + idempotent ShopDeck writeback
    enqueue, extracted out of Exotel's `_submit_pending_ndr_outcome()`. This is the actual
    shared core both providers use to get an outcome into ShopDeck's queue.
  - `map_sarvam_reschedule_decision()` - maps Sarvam's `date_1_confirmed | date_2_confirmed
    | declined | undecided` onto the same internal intent vocabulary
    `classify_reply_heuristic()` produces, so both paths share one `to_shopdeck_vocabulary()`
    call and one enqueue path.
- `exotel_webhooks.py`'s `build_session_constants()` and `_submit_pending_ndr_outcome()` now
  delegate to the shared functions above instead of inlining the logic. **Behavior is
  unchanged** - verified via the full relevant test suite before and after, identical
  pass/fail counts.

### 3. Sarvam's inbound webhook handlers (new, real code)
`src/api/webhooks/sarvam_webhooks.py` (new router, wired into `src/main.py` additively):
- `POST /api/customer-engagement/voice/sarvam/on-start` - resolves the engagement directly
  by `engagement_id` (expected in the hook payload's metadata) and returns a flat
  `{variable_name: value}` map built from the shared allow-list. **No Exotel-style
  correlation-resolution complexity needed** - Sarvam's variable system carries
  `engagement_id` through the whole call for free, so a direct `repo.get_engagement()` lookup
  suffices.
- `POST /api/customer-engagement/voice/sarvam/call-outcome` - the real endpoint meant to
  eventually replace the Postman Echo mock currently configured on `push_ndr_call_outcome`.
  Takes Sarvam's already-decided outcome (no heuristic classification needed - the voice
  agent's own LLM decides `reschedule_decision` directly) and enqueues it via the shared
  writeback path. `alternate_phone_number` and `address_confirmed_same_pincode` (capabilities
  Exotel's pipeline never had) go into ShopDeck's `action_parameters` field, confirmed
  genuinely free-form against the real schema at
  `/Users/sumatidhingra/Documents/AaramBooks/business_systems/shopdeck/backend/api/schemas/ndr_queue.py`
  - not guessed. `failure_reason` (also new) folds into `reasoning` text since ShopDeck has
  no dedicated field for it.
- Both endpoints are **import-verified and unit-testable but have never received a real
  Sarvam webhook call**. The exact payload shape Sarvam sends to an on-start hook, and the
  exact auth header format, are reconstructed best-effort from incomplete public docs -
  `verify_sarvam_bearer()`'s docstring says this explicitly. Treat as needing correction
  once a real delivery is inspected.
- `SARVAM_WEBHOOK_SECRET` added to `.env.example` / `src/shared/config.py` alongside the
  already-configured `SARVAM_API_KEY` (confirmed loaded, 36 chars, value never printed).

## 2026-09-13 update: production deployment, bugs found and fixed, and the queue investigation

### Bugs found and fixed (all committed and deployed, not left as notes)

1. **`_clean_customer_name` (`ccc_builder.py`) was corrupting real customer names.** A
   Gemini-added heuristic meant to fix concatenation artifacts (`DeepaGupta` → `Deepa Gupta`)
   was also breaking legitimate names on real, verified inputs: `McDonald` → `Mc Donald`,
   `O'Brien` → `O'brien`, `D'Souza` → `D'souza` (a common real Indian surname, not an edge
   case), and a false-positive class where a genuinely two-part name like `Krishnan Nan`
   got wrongly truncated to `Krish Nan` because "krishnan" happens to end in "nan" - common
   in Indian names. Fixed by restricting the concatenation-fix heuristics to only run on
   names that arrive as a single unbroken token (the actual signature of the bug being
   targeted) and adding name-aware capitalization that preserves `Mc`/apostrophe surnames.
   Verified against all of the above cases directly, not just reasoned about.
2. **`instruction_product_description` was missing from Sarvam's `agent_variables`.**
   Confirmed via a real Sarvam Instant Outbound curl example the user provided, showing
   Sarvam's actual configured agent expects this key. Exotel already got it (via
   `get_instructions_for_domain()`); Sarvam's adapter never called that function at all.
   Fixed by routing it through the same allow-list mechanism
   (`ndr_voicebot_context_variables.json` + `build_provider_call_variables()`), not by
   copying Exotel's full instruction set - the other 14 `instruction_*` strings are
   deliberately excluded for Sarvam (baked into its static persona instead, confirmed by an
   existing code comment), and Sarvam's own real schema only declares this one as a per-call
   variable.
3. **`DEFAULT_VOICE_PROVIDER` was a hardcoded `"EXOTEL"` constant with no way to change it
   short of a code edit.** Since the NDR orchestrator never sets `voice_provider` explicitly
   on any real dispatch, every single real NDR call - regardless of intent to test Sarvam -
   was silently going out via Exotel. This is the actual reason real NDRs kept getting
   consumed without ever producing a Sarvam test: they were being dispatched, just via the
   wrong provider, then exhausting their 2 retries and landing in `permanently_failed`.
   Fixed by making it a real setting (`settings.default_voice_provider`, defaults to
   `"EXOTEL"` so nothing else changes), and setting `DEFAULT_VOICE_PROVIDER=SARVAM`
   specifically in the VPS's own `.env`.
4. **AZM's persistent Postgres provider and its own init script** - covered fully in
   `docs/BRAIN_DEPLOYMENT_RUNBOOK.md` and `docs/claude/DEPLOYMENT_STRATEGY_BRAIN_VPS.md`,
   not repeated here since it's not Sarvam-specific, but relevant context: these fixes shipped
   in the same deploy cycle as the Sarvam fixes above.
5. **No calling-hours check existed anywhere in the dispatch pipeline.** Raised directly by
   the user after seeing the poller claiming every 15 seconds: an NDR becoming eligible at
   2 AM would have been called at 2 AM, via whichever provider was dispatched to (Sarvam now,
   previously Exotel). Fixed in `src/intelligence_domains/ndr/config.py`
   (`NDRSettings.is_within_calling_hours()`, real India-Standard-Time check via
   `zoneinfo`) and wired into `NDRQueuePoller._poll_loop()` *before* it ever attempts a claim
   - an NDR outside the calling-hours default window is left completely untouched in
   ShopDeck's queue, not claimed and given back. Verified with real boundary-time test cases
   against the original 9 AM-7 PM default (2 AM/8 AM blocked, 9 AM/6 PM allowed, 7 PM/11 PM
   blocked) and the full regression suite (26 failed/8 errors, identical to the standing
   pre-existing baseline - zero new). The start hour was later moved from 9 AM to 11 AM
   (same 2026-09-13, per business decision) by changing
   `NDRSettings.calling_hours_start_ist`'s default from `9` to `11` - the gate logic itself
   (`is_within_calling_hours()`) is unchanged, so this was a config-value change, not a
   re-verification of the boundary logic (zero new regressions from that change either).
   Current default window is **11 AM-7 PM IST** (extended to 11 PM via a VPS-only
   `NDR_CALLING_HOURS_END_IST=23` override in `.env` on 2026-09-14 specifically to allow
   real testing against a backlog; not committed to the repo default, remove the `.env` line
   to fall back to 7 PM once testing is done). This applies to both Sarvam and Exotel
   equally, not a Sarvam-specific gate.
6. **Retry idempotency bug silently killing NDRs after their first failure, for any
   reason.** `CustomerEngagementRepository.create_engagement` raised `ValueError` whenever a
   retry's `action_request_id` didn't match the one stored from the first attempt - which it
   never would, since the orchestrator regenerates a fresh random `action_request_id` on
   every single run (`orchestrator.py`, `f"act_{uuid.uuid4().hex[:8]}"`), while
   `NDRQueuePoller` derives `engagement_id` deterministically from `queue_item_id`
   specifically so retries converge on one record. Found by tracing a real permanently-failed
   queue item (AWB `142285243044206`) back through VPS logs: its first attempt actually
   reached Sarvam and failed for an unrelated reason (see bug 7 below); its one retry then
   died instantly on this idempotency check instead of ever reaching Sarvam again. 5 of 14
   permanently-failed items on the VPS at the time carried this exact failure signature -
   the single most common failure reason, ahead of any real provider-side cause. Fixed in
   `src/infrastructure/adapters/customer_engagement/repository.py` - a colliding
   `engagement_id` is now always treated as the same logical engagement and returned as-is,
   since `action_request_id` isn't a meaningful dedup key at this call site. Added a
   regression test (`test_create_engagement_retry_with_different_action_request_id_reuses_existing`)
   exercising the real `DuplicateKeyError` path via `setup_indexes()` - previously this path
   had zero test coverage.
7. **`TEST_PHONE_OVERRIDE` was in the wrong phone format for Sarvam - the actual root cause
   blocking the first real call.** Sarvam's API requires E.164 (`+91...`); the VPS's (and
   local's) `.env` had it as Indian local format (`08168583367`), so Sarvam rejected every
   real dispatch attempt with a 422 (`Invalid phone number format`). This is a `.env`-only
   value (not committed, contains a real phone number), fixed directly in both the VPS and
   local `.env` files to `+918168583367`. This was found only by reading full VPS log
   history for a specific queue item, since bug 6 above meant the retry's failure (the
   misleading idempotency error) was the only one visible from ShopDeck's queue table itself.
8. **The poller could dispatch the next call before the previous one's live conversation
   ended.** `max_concurrent_calls=1` only bounded how many claim/dispatch *pipelines* could
   run at once - the semaphore released the instant a call was dispatched, not when it
   finished, so a backlog of eligible NDRs could have produced several real calls in quick
   succession onto the same test number. Raised directly by the user before testing began
   ("once the call ends then only brain should dispatch another call... I don't want brain
   firing 20 calls simultaneously on my number"). Fixed by having
   `NDRQueuePoller._process_claimed_item` return the dispatched `engagement_id`, and having
   `_process_task_wrapper` (the live poll-loop path only - `process_next_item()`'s
   test/certification single-shot path is deliberately untouched, since it bypasses the
   semaphore and tests don't simulate a webhook arriving) await
   `_wait_for_call_completion` before releasing the semaphore. That method polls the
   engagement every `NDR_CALL_COMPLETION_POLL_SECONDS` (default 5s) until Exotel/Sarvam's
   webhook flips it to `COMPLETED`/`FAILED`/`ESCALATED`, capped by
   `NDR_CALL_COMPLETION_MAX_WAIT_SECONDS` (default 600s) so a missed webhook can't hang the
   poller forever. Verified live on the VPS: across 4 real dispatched calls, exactly one
   claim was ever in flight at a time, with the next claim only appearing in the logs after
   the previous engagement reached a terminal state.
9. **Real customer phone numbers were rejected by Sarvam - the actual reason zero real
   customers were called on 2026-09-15, a full day after `TEST_PHONE_OVERRIDE` was
   removed.** Found while checking "did today's real dispatches actually work": 26 items
   went to `permanently_failed` that day, every one with `Sarvam HTTP 422: ... Invalid
   phone number format` on a real 10-digit customer number (e.g. `9883696900`). Root cause:
   `SarvamVoiceBotAdapter.dispatch_call` passes `action_request.parameters["customer_phone"]`
   straight through with zero formatting - this was masked for a full day because
   `TEST_PHONE_OVERRIDE` happened to already be manually set in E.164
   (`+918168583367`, fixed in bug 7), so nobody had touched or tested the actual
   real-customer phone hydration path at all. The moment the override was removed, every
   real dispatch hit this. Fixed in `src/shared/phone_format.py` (new, `to_e164_india`) -
   handles bare 10-digit, leading-0, 91-prefix-without-+, already-E.164, and stray
   spaces/dashes, leaving a genuinely unexpected format unchanged rather than guessing -
   applied in `sarvam_adapter.py` right before dispatch. Added
   `tests/shared/test_phone_format.py` (9 cases). Verified live: `to_e164_india('9883696900')`
   → `'+919883696900'` inside the redeployed container. Deliberately scoped to Sarvam only -
   Exotel's required format has never been confirmed, and `EXOTEL_CALLER_ID` is stored in a
   different (leading-zero) format, so applying this to Exotel without verification first
   could break it instead of fixing anything. 3 queue items still had a retry left
   (`failed_retryable`) when this was fixed, past calling hours for the day - they'll be
   picked up automatically once the window reopens (11 AM IST) if still eligible then; watch
   whether they succeed as the first real proof this fix works end-to-end.
10. **`engagement_registered` queue-status transition was skipped on retry, mis-tracking real
    dispatches.** ShopDeck's `/engagements` POST endpoint's implicit queue-status side effect
    only fires on genuinely fresh registration, not on an idempotent re-registration during a
    retry (Brain's `engagement_id` is deterministic per `queue_item_id`, by design - see bug
    6). This left `queue_status` stuck at `claimed` for retried items, causing a real `409
    Conflict` on the later `call_dispatched` transition *after* Sarvam had already placed a
    real call - the call itself succeeded, but ShopDeck's own queue record didn't reflect it.
    Fixed with an explicit, 409-tolerant `update_queue_status(status="engagement_registered",
    ...)` call in `ndr_queue_poller.py` right after registration, before dispatch.
11. **`address_change_requested`/`phone_no_change_requested` boolean-vs-string bug silently
    dropped `new_address_details`/`new_phone_number` from every real call.** The original
    check was `== "yes"`, matching the string form the agent-config docs describe - but every
    real Sarvam payload actually observed in production sends a genuine JSON boolean instead
    (`True`/`False`), so `True == "yes"` was always `False`. Found 2026-09-15 by checking a
    real production result row (AWB `24899810621600`) where the customer gave a new phone
    number that Sarvam correctly captured in the transcript, but which never reached
    `ndr_intelligence_results`. This bug existed from when the feature was first written -
    it had simply never been caught, because the existing tests used the documented string
    form and passed unchanged even after the fix (proving they'd never have caught the real
    bug). Fixed in `src/api/webhooks/sarvam_webhooks.py` with an `_is_affirmative()` helper
    that accepts both representations; added a new boolean-based regression test
    (`test_new_phone_number_lands_in_action_parameters_when_flag_is_a_real_boolean`).
12. **Call recording fetch 404'd on every real call - see "Call recording capture pipeline"
    section below for full detail.** Summarized here for the bug list: fetching the
    recording from Sarvam's analytics endpoint synchronously inside this same webhook failed
    with a 404 for every single real call on 2026-09-16, because the recording isn't
    processed and available on Sarvam's side the instant the completion webhook fires.
    Fixed by moving the fetch into a background retry worker instead of one inline attempt.

### The queue investigation - why a real Sarvam call took this long to complete (historical - resolved 2026-09-14)

This section documents why no real Sarvam call had completed as of 2026-09-13. It has since
been resolved (see the TL;DR and bugs 6-9 above) - real calls now complete successfully.
Kept here as-is because the underlying investigation (queue enrollment, the COD filter,
courier ingestion lag) is still accurate background for how ShopDeck's NDR queue behaves,
independent of Brain's own bugs. Traced end to end, with real evidence at every step,
together with the ShopDeck-side agent:

1. The VPS's `claim_ndr_work` call returned `204 No Content` on every attempt for 24+ hours
   straight, with zero errors - ruling out a Brain-side claim bug immediately (a broken
   claim call would show errors or inconsistent behavior, not a clean, consistent empty
   response).
2. ShopDeck's queue was not actually empty - the real production `ndr_queue` table had ~35
   items, but every one had already progressed past `eligible` (`engagement_registered`,
   `action_ready`, `call_dispatched`, `permanently_failed`, etc.) - there was genuinely
   nothing left to claim, not a bug hiding real eligible items.
3. Enrollment itself (raw NDR → claimable queue row) is governed by a hard-coded SQL filter
   in ShopDeck's own repo (`backend/api/repositories/ndr_queue.py`,
   `enroll_eligible_ndrs()`): `ndr_status='pending' AND order_status='dispatched' AND
   payment_mode='cod' AND delivery_time IS NULL`, joined against `customer_info` requiring a
   non-empty `customer_number`. Confirmed a real, related data-quality bug already documented
   in ShopDeck's own sync script comments (a `customer_info` upsert issue affecting exactly
   this join). ShopDeck's own agent confirmed 5 new items enrolled the same day a
   `customer_info` fix landed - direct evidence the pipeline works correctly once the
   underlying data is right, this was never a broken pipeline.
4. **The real reason the queue looked perpetually empty**: two separate Brain instances -
   the VPS deployment and the developer's local dev server - were both authenticating to
   ShopDeck as the exact same service-account identity (`sa:sa-aaram_brain-225eca38`, since
   both `.env` files had the identical real `BRAIN_CLIENT_ID`) and both continuously polling
   the same production queue. Confirmed directly: local Brain's `.env` pointed at real
   production Identity/ShopDeck (not a local sandbox) for this entire session, and its NDR
   Queue Poller auto-starts and polls every 15 seconds on boot - so whenever the local dev
   server happened to be running alongside the VPS, they were racing for the same trickle of
   real, enrollment-filtered NDRs. ShopDeck's own claim log can't distinguish them - `claimed_by`
   only records the authenticated identity, not the calling machine/process - so this was
   only solvable by checking Brain's own config, not from ShopDeck's data alone.
5. **Resolved**: local Brain's dev server was stopped (no longer racing with the VPS), and
   the VPS's `default_voice_provider` was fixed to `SARVAM` (see bug #3 above) so that when a
   fresh, genuinely eligible NDR does land, it will actually produce the Sarvam test that's
   been the goal, instead of silently going out via Exotel and burning its retries. The VPS's
   own poller is running unattended right now and will pick up the next real eligible item on
   its own - no further manual action needed on Brain's side.

## 2026-09-16 update: call recording capture pipeline

**Why this exists**: the shipping partner needs call recordings for priority escalation on
difficult NDRs, and ShopDeck had nowhere to store them. Sarvam's completion webhook itself
never carries a usable recording - its `recording_url` field has been observed `null` on
every real call. The actual recording is retrievable from a separate, pull-based endpoint:
`GET https://apps.sarvam.ai/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/recordings/
{interaction_id}` (`X-API-Key` header), which returns the raw WAV binary directly, not JSON
(contradicts Sarvam's own doc sample code, which calls `response.json()` - confirmed
empirically, with and without `Accept: application/json`, both times binary).

**What was built**: `src/infrastructure/adapters/customer_engagement/recording_storage.py`
(`fetch_and_store_recording()`) fetches the WAV from Sarvam and re-hosts it on Cloudflare R2
(`boto3` against R2's S3-compatible API, `endpoint_url` = the account's R2 endpoint,
`region_name="auto"`) at `sarvam_call_recordings/{awb_no}/{engagement_id}.wav`, behind a
custom domain (`https://recordings.aarambooks.cloud`) rather than the `r2.dev` subdomain
(Cloudflare's own docs say that one isn't suitable for production). The resulting public URL
is reported to ShopDeck via `ShopdeckCemAdapter.update_queue_status(status="call_completed",
recording_url=...)` - **deliberately not** via `ndr_intelligence_results.action_parameters`,
by explicit user decision (2026-09-16): a recording is reference/audit material, not
something a human needs to act on, so it belongs on ShopDeck's `ndr_engagements.recording_url`
column (which ShopDeck's side added specifically for this) instead of mixing with the
action-required fields. This must fire even for calls with no decisive `call_outcome`, since
the recording is still real, useful evidence regardless.

**Bug 12, found the same day it was wired to real live traffic**: fetching the recording
synchronously inside the call-completed webhook handler 404'd for every real call on
2026-09-16 - confirmed directly in brain-api logs. Re-fetching the exact same URL minutes
later succeeded (`200 audio/wav`, correct byte count) - Sarvam's analytics endpoint simply
isn't ready to serve the recording the instant its own completion webhook fires; there's an
unspecified processing delay on Sarvam's side. As a side effect, this also silently blocked
`update_queue_status` from ever firing for the 4-of-6 real calls that day with no decisive
`call_outcome`, since the recording-success path had accidentally become the only thing that
advances `queue_status` past `call_dispatched` for those calls.

**Fix**: moved the fetch out of the synchronous webhook entirely into a new
`RecordingFetchWorker` (`src/workers/recording_fetch_worker.py`), backed by a new
`recording_fetch_queue` Mongo collection with the exact same claim/lease/backoff pattern as
the existing `OutboundWritebackWorker` (`repository.py`'s `enqueue_recording_fetch` /
`claim_pending_recording_fetch` / `mark_recording_fetch_success` /
`mark_recording_fetch_transient_retry` / `mark_recording_fetch_dead_letter`). The webhook
handler now only calls `repo.enqueue_recording_fetch(...)` - no more Sarvam/R2/ShopDeck HTTP
calls inline. The queue item's first attempt is deliberately delayed 90s (not tried
immediately, since an immediate attempt just reproduces the same 404), then retries with
exponential backoff (1, 2, 4, 8, 16, 32, 60, 60 min - roughly 2 hours of window) before
dead-lettering.

**A real ShopDeck-side quirk this fix depends on, worth knowing if this ever needs
revisiting**: read directly from ShopDeck's own route source
(`business_systems/shopdeck/backend/api/routers/ndr_queue.py`, local checkout at
`/Users/sumatidhingra/Documents/AaramBooks/business_systems/shopdeck/`) - the PATCH
`.../queue/{id}/status` handler writes `ndr_engagements.recording_url` **unconditionally**
whenever `status == "call_completed"` is sent, via its own connection, **before** it
validates the queue_status transition itself. So when the recording worker's report arrives
late (after some other event, like the outcome writeback, has already advanced the queue
past `call_dispatched` to `action_ready`), the transition validation correctly rejects
`call_completed` with a 409 - but the `recording_url` write has already landed regardless.
`RecordingFetchWorker` treats that specific 409 as success, not a reason to retry (confirmed
directly against real production data: AWB `142285242291216`'s recording_url landed despite
a live 409 in the exact predicted shape). **This depends on ShopDeck's current (loose)
ordering of those two DB operations** - if they later wrap both in one transaction, a late
report would start failing silently again and would need a genuinely separate endpoint
instead (decoupled from the queue status-transition validator entirely, which is closer to
the original architectural intent - recording_url isn't queue state).

**Verified end-to-end against real production data, 2026-09-16**: unit tests (15/15,
`tests/api/webhooks/test_sarvam_call_completed.py` +
`tests/workers/test_recording_fetch_worker.py`), plus a real local run against production
Sarvam/R2/ShopDeck that backfilled both of that day's two real missing recordings (AWB
`142285242291216` and `142285242800562`) as a side effect - both now show a real
`recording_url` in ShopDeck's production `ndr_engagements` table and a real WAV file in R2.
**Not yet deployed to the VPS** - committed locally only, pending explicit deploy
permission per standing project rule (see `no-deploy-without-explicit-permission` in
Claude's session memory). Until deployed, the live webhook path is still running the old
inline-fetch code, which will keep failing silently on every real call.

## What's NOT built yet, and why

**Design decision (supersedes everything below about Stream Cohort/campaigns in earlier
history of this doc): use Instant Outbound.** Per real docs (`/conversations/api/
instant-outbound/create.md` and `/webhook-payload.md`):

```
POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds
Header: X-API-Key: <api_key>

{
  "app_config": {
    "app_id": "<agent_id>", "app_version": <integer>, "app_type": "agent",
    "connection_config": {"connection_id": "<connection_id>", "agent_phone_number": "<phone>"},
    "agent_variables": {"engagement_id": "...", "customer_name": "...", "...": "..."}
  },
  "user_config": {"user_phone_number": "<customer_phone>"},
  "webhook_config": {"url": "<brain completion endpoint>", "metadata": {"engagement_id": "..."}}
}
```
Response: `{"attempt_id": "..."}` - immediate, synchronous, real correlation ID. No
persistent campaign needed (unlike Stream Cohort), no separate on-start hook needed (variables
travel in the creation request itself), no polling needed. The completion webhook (fired once,
per call) carries `attempt_id`, `status` (`connected`/`no_answer`/`busy`/`failed`),
`interaction_id`, `failure_reason`, `interaction_transcript` (full transcript, `role`/`en_text`
per turn), and `webhook_config` echoed back verbatim (so `metadata.engagement_id` round-trips
for free).

**Config status - all resolved as of 2026-09-13:**
- ✅ `org_id`, `workspace_id`, `agent_id`, `connection_id`, `phone_number`, `api_key` - all
  live and verified loaded in `src/shared/config.py` (agent_id has since changed at least
  once as the user iterated on the agent - `sarvam_agent_id` in the real `.env` is the
  current source of truth, not the value quoted earlier in this doc).
- ✅ `app_version = 23` - **real, committed value**, confirmed directly by the user via a
  real Sarvam Instant Outbound curl example on 2026-09-13. No longer the draft `4`.
- ✅ `SARVAM_WEBHOOK_SECRET` - real value set, verified working (`verify_sarvam_bearer()`'s
  `?secret=` query-param mechanism, confirmed by real test coverage in
  `tests/api/webhooks/test_sarvam_call_completed.py`).

**Code status - written and verified, not yet tested against a real Sarvam call:**
1. `SarvamVoiceBotAdapter` (`src/infrastructure/adapters/customer_engagement/
   sarvam_adapter.py`) - **written**. `provider_name = "SARVAM"`, `dispatch_call()` builds
   the exact Instant Outbound request shape above, reads the just-created engagement record
   to build `agent_variables` via the shared `build_provider_call_variables()`, same
   fail-fast/no-auto-retry discipline as `ExotelVoiceBotAdapter`. Registered into
   `CustomerEngagementExecutor`'s `adapters` dict in `src/main.py` (`{"EXOTEL": ...,
   "SARVAM": sarvam_adapter}`) - additive, Exotel's registration unchanged.
2. `sarvam_webhooks.py` - **rewritten**. The old `/on-start` + `/call-outcome` two-endpoint
   design (built for the superseded Stream Cohort/tool-call approach) is gone, replaced by a
   single `/call-completed` handler matching Instant Outbound's one real completion webhook.
   It classifies the last customer transcript turn via the same `classify_reply_heuristic()`
   Exotel uses, then calls the same shared `enqueue_ndr_intelligence_result()` - no separate
   pending/final split needed, since Instant Outbound reports once, already finished.
   `map_sarvam_reschedule_decision()` (built for the old tool-call design) was removed from
   `reply_parser.py` as dead code under this design, not left around to confuse a future
   reader into thinking two Sarvam paths coexist.
3. **Verified**: full import chain (`sarvam_adapter.py`, `sarvam_webhooks.py`, `src.main`)
   loads cleanly, `executor.adapters` has both `EXOTEL` and `SARVAM`, exactly one Sarvam
   route registered (`/api/customer-engagement/voice/sarvam/call-completed`), transcript
   extraction logic unit-tested inline. Full regression suite re-run after wiring this in:
   identical 51 passed / 5 pre-existing-unrelated-failed to every prior baseline this
   session - zero regressions from adding a second live provider.
4. **NOT yet verified**: a real Sarvam call has never been placed. Everything above is
   correct per documented API shapes, not proven against a live response. Do not treat this
   as production-ready until a real end-to-end test has run (see next steps) - and don't run
   that real test until `app_version` is committed, not draft `4`.

**Still not verified against a real live call**: actual call latency, real completion webhook
payload shape (confirm it matches the docs exactly), and whether `agent_variables` keys must
exactly match variables configured on the agent (per the docs' own wording elsewhere in this
platform) - i.e. the agent's variable list and this dict's keys need manual sync-keeping.

## Decisions already made (don't re-litigate)

- **Telephony: rent numbers directly from Sarvam.** No Exotel or Twilio account underneath.
  Full break from Exotel is the actual goal, not a partial one - Sarvam's own example configs
  route through an Exotel connection by default, which is explicitly NOT what's wanted here.
- **Shared logic gets extracted, not duplicated**, even though this touches
  `exotel_webhooks.py`'s file contents - explicitly decided when the classification-logic
  extraction question came up, and applied consistently to the later writeback-enqueue
  extraction too. The bar is behavior preservation (verified via tests), not "don't touch the
  bytes."
- **`reschedule_decision: "undecided"` maps to the same ShopDeck vocabulary as `UNCLEAR`**
  (`escalate`/`unclear`) - resolved via `map_sarvam_reschedule_decision()`, not left open.
- **`failure_reason` goes into `reasoning` text**, not a new ShopDeck schema field - resolved,
  not left open.

## Test/mock artifacts already produced

- `docs/claude/SARVAM_MOCK_TEST_SETUP.md` - input variables, a condensed system prompt
  (Persona/Objective/Context/Guardrails/Steps model), and a Mock (Postman Echo) tool config
  for `push_ndr_call_outcome`, for testing entirely inside Sarvam's dashboard with no real
  Brain endpoint. **User has already run this test** (confirmed in conversation) - the actual
  transcript/echoed-payload results from that test have not yet been reported back or
  reviewed here; worth getting that output before trusting the persona draft in that doc as
  final.
- The full 835-line `docs/voicebot/bot_persona.txt` has NOT been ported to Sarvam's model -
  the mock-test doc's system prompt is a condensed version sufficient to run one test
  conversation, not a complete port. A real production system prompt still needs the full
  persona's nuance (interruption handling, empathy rules, response-length discipline, etc.)
  folded in properly.

## Recommended next steps, in order (updated 2026-09-15)

1. ~~Get `org_id`, `workspace_id`, `agent_id`, `connection_id`, `phone_number`, `api_key`~~ -
   **Done.**
2. ~~Write `SarvamVoiceBotAdapter.dispatch_call()`~~ - **Done.**
3. ~~Rewrite `sarvam_webhooks.py`~~ - **Done.**
4. ~~Commit the agent's draft version and update `sarvam_app_version`~~ - **Done**, real
   value `23`.
5. ~~Set a real `SARVAM_WEBHOOK_SECRET` and `SARVAM_WEBHOOK_BASE_URL`~~ - **Done.**
6. ~~Fix `default_voice_provider` so real dispatches actually go to Sarvam~~ - **Done**,
   `DEFAULT_VOICE_PROVIDER=SARVAM` live on the VPS as of 2026-09-13.
7. ~~Let one real, genuinely eligible NDR actually reach the VPS's poller and complete a
   real Sarvam call~~ - **Done, 2026-09-14.** Multiple real calls completed successfully
   (and one `busy`/`FAILED` outcome handled correctly too), dispatched sequentially, with
   outbound writeback confirmed firing. See the TL;DR and bugs 6-8 above for what it took to
   get here (idempotency bug, phone-format bug, sequential-dispatch gate).
8. ~~`NDR_CALLING_HOURS_END_IST=23` temporary testing override on the VPS~~ - **Reverted,
   2026-09-14.** The VPS `.env` no longer sets this; the real 7 PM default
   (`calling_hours_end_ist` in `config.py`) is back in effect and confirmed live.
9. ~~`TEST_PHONE_OVERRIDE` removed from the VPS~~ - **Done, 2026-09-14** (explicit user
   decision) - **but this alone did not mean real customers were being called.** See item 10.
10. ~~Real customer phone numbers rejected by Sarvam (E.164 bug)~~ - **Done, 2026-09-15.**
    See bug 9 above. Every real dispatch failed for a full day after item 9 - this is the
    fix that actually made real calls to real customers possible, not the override removal
    itself. **Not yet independently confirmed with a successful real call** - 3 queue items
    with a retry left will be picked up automatically once calling hours reopen; check
    whether they succeed as the first real proof.
11. ~~Review real call quality on real-customer calls~~ - **Partially done.** Real customer
    transcripts (via a CSV export from Sarvam's bot platform) were read directly on
    2026-09-16 as part of investigating the recording-capture bug - the two calls that
    reached a decisive outcome that day both produced coherent, correctly-parsed reschedule
    dates matching what the customer actually said. `SARVAM_CALL_QUALITY_REVIEW_2026-09-14.md`
    still only covers the earlier test-number calls, not a dedicated review of real-customer
    call quality specifically. Still open: does the webhook payload Sarvam actually sends
    match what `sarvam_webhooks.py` expects field-for-field, with no silently-dropped or
    defaulted values? (Bug 11 above is one real example where the answer was "no.")
12. **Still open, urgent: full production system-prompt port.** Real customers are being
    reached with the condensed test-version prompt, not the full 835-line persona
    (`docs/voicebot/bot_persona.txt` - interruption handling, empathy rules, response-length
    discipline, etc.).
13. **New, from 2026-09-16: deploy the recording-fetch reliability fix (bug 12) to the VPS.**
    Committed locally, verified end-to-end against real production data, but the live webhook
    path is still running the old code that silently fails on every call - needs explicit
    deploy permission per standing project rule before this is fixed in production, not just
    on record.
14. **New, from 2026-09-16: clarify with ShopDeck whether `ndr_status` downstream consumption
    of `action_ready` items is expected to lag.** Checked two real same-day rescheduled calls
    with identical Brain-side writeback correctness: one showed `shipment_ndr_reports.
    ndr_status = 'reattempt_requested'` (fully consumed downstream), the other still showed
    `'pending'` despite `ndr_queue.queue_status` reaching `action_ready` for both at roughly
    the same time. Brain's own writeback is confirmed correct in both cases (checked directly
    against `ndr_intelligence_results`); this looks like a ShopDeck-side downstream
    inconsistency, not a Brain bug - worth raising with ShopDeck rather than assuming.
15. Only after the above: any decision to move real production call traffic off Exotel
    entirely - Exotel still exists and still works, this hasn't been forced by anything
    above.
