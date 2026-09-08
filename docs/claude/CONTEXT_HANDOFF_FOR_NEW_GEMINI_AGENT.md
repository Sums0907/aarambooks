# Context handoff — NDR Conversation Mission/State Contract, Physical Gate 3

Written by: Claude
Date: 2026-09-08
Why this exists: the previous Gemini agent session crashed mid-edit without notifying the
user. This is a full state-of-the-world handoff so a new agent doesn't have to reconstruct
today's work from scratch, doesn't duplicate it, and doesn't miss the one thing left in a
genuinely broken state.

**Read this whole document before touching any file.** The most urgent item is section 1.

---

## 0. Nothing today is committed

`git log` still shows the last real commit as "Add certification script," from before this
session started. Everything described below is **uncommitted working-tree state only**.
`git status --short` at the moment of writing this:

```
 M docs/ag_chat_ndr_ID_log_2.md
 M docs/voicebot/bot_persona.txt
 M scripts/certify_gate2.py
 M src/api/webhooks/exotel_webhooks.py
 M src/brain_core/action_engine/contracts.py
 M src/brain_core/context_engine/ccc_builder.py
 M src/brain_core/context_engine/ccc_contracts.py
 M src/infrastructure/adapters/customer_engagement/repository.py
 M src/infrastructure/adapters/shopdeck_cem_adapter.py
 M src/intelligence_domains/ndr/reply_parser.py
 M src/main.py
 M src/workers/ndr_queue_poller.py
 M tests/api/webhooks/test_dynamic_greeting.py
 M tests/test_ndr_queue_e2e_local.py
?? .agents/rules/multi-agent-workflow.md
?? business_systems/shopdeck/docs/master_deployment_runbook.md
?? docs/03-intelligence-domains/ndr-intelligence/GATE3-PASS-MASTER.md
?? docs/09-decisions/GATE3-PASS-MASTER.md
?? docs/claude/                          (Claude's review/audit docs - read these for detail)
?? dump_transcript.py / format_transcript.py / parse_transcript.py
?? scripts/certify_gate3_writeback.py
?? scripts/inspect_debris.py
?? scripts/run_one_real_call.py
?? scripts/teardown_test_debris.py
?? src/intelligence_domains/ndr/mission_factory.py
?? tests/test_ndr_behavioral_scenarios.py
?? tests/test_ndr_mission_contracts.py
```

Do not assume anything is safe just because it's on disk. Nothing has a git checkpoint yet.

---

## 1. URGENT — the crashed agent left a real regression in `generate_dynamic_greeting`

This is almost certainly what the previous agent was mid-editing when it crashed
(`src/api/webhooks/exotel_webhooks.py`, function `generate_dynamic_greeting`, currently
around line 155). The file is syntactically valid and the local server is up - this is a
**behavioral** bug, not a crash-causing one.

**What's wrong:** the closing line is now:

```
क्या हम आपकी delivery कल के लिए reschedule कर दें?
("Shall we reschedule your delivery for tomorrow?")
```

This is precisely the pushy, premature reschedule-ask that the original task explicitly
banned (requirement 9: "do not immediately force 'are you available tomorrow?'") and that
this exact function's own docstring - two lines above the offending code - still says it must
never do: *"it ends by asking whether now is a convenient time - never with a delivery-date
ask."* The code no longer matches its own contract.

**What's genuinely good and should be KEPT, not reverted:** the same edit made the greeting
voice the actual failure reason (`mission_why_this_call`) instead of withholding it as
internal jargon (which is what it did earlier today). That's a real, defensible improvement -
more transparent to the customer, and nothing in it is unsafe to say aloud. Don't throw this
out fixing the consent-line bug.

**The fix, precisely:** replace the final line back to a convenience/consent question (not a
date ask) - e.g. restore something equivalent to `"क्या अभी बात करना सुविधाजनक है?"` - while
leaving the `why_failed` reason-voicing logic above it untouched.

**Proof this is broken, not just a stylistic disagreement:** three tests in
`tests/test_ndr_mission_contracts.py` now fail because of this, and they are failing
correctly - do not "fix" them by loosening the assertions, fix the function:
- `test_greeting_states_the_failed_delivery_and_never_opens_with_how_can_i_help`
- `test_greeting_ends_with_consent_and_contains_no_reschedule_ask`
- `test_greeting_omits_absent_facts_rather_than_guessing`

Run `python3 -m pytest tests/test_ndr_mission_contracts.py -v` after fixing to confirm all
19 pass again.

**One more loose end in the same area, lower urgency:** the same crashed session had also
started editing `docs/voicebot/bot_persona.txt`, adding a new `instruction_no_stalling` rule
("never say you will check or look up, you already have the information") and reiterating
`instruction_lookup_rule` / `instruction_not_pushy` as "absolute laws" the persona will treat
as dynamically injected. This part of the edit is good and directly targets a real bug (see
section 3). But `instruction_no_stalling` **does not exist anywhere in
`build_session_constants()`** in `exotel_webhooks.py` - the persona now expects a key that
never actually gets sent. Add it: something like `session_constants["instruction_no_stalling"]
= "Never say you will check, look up, or verify anything, or ask the customer to wait. You
already have every fact you're going to have for this call. Answer immediately or say the
fact is unavailable."` Keep it consistent with the wording already in `bot_persona.txt`.

---

## 2. What actually got built and verified today (all real, all tested against live data)

In order:

1. **`ConversationMissionContract` / `NDRConversationState`** -
   `src/brain_core/action_engine/contracts.py`,
   `src/intelligence_domains/ndr/mission_factory.py` (new file). Nine approved state names,
   mission fields, `effective_allowed_actions` resolving a duplicate-field collision between
   the directive and the mission.
2. **Flat `mission_*` fields on `CustomerConversationProjection`** and the webhook
   allow-list extended to match - `ccc_contracts.py`, `ccc_builder.py`,
   `build_session_constants()` in `exotel_webhooks.py`.
3. **Greeting rewritten to be deterministic and Hindi-first** - then partially regressed by
   the crash (see section 1).
4. **ShopDeck writeback fixed twice over**: first the schema/auth (was using a
   never-set `settings.shopdeck_token`; now correctly reuses
   `ShopdeckCemAdapter.submit_intelligence()`, which authenticates via the real Aaram
   Identity M2M flow). Then a second, much bigger bug: `raw_transcript` extraction was
   reading `payload.get("transcript")` / `payload.get("TranscriptionText")`, **neither of
   which exists anywhere in Exotel's real payload** - the real customer text is nested at
   `payload["events"][*]["event_data"]["transcript_segments"][*]`. This meant the writeback
   had **never fired on any real call, ever**, despite passing every test, because every test
   used a hand-built payload shape that didn't match reality. Fixed via
   `extract_customer_utterance()`, verified directly against real captured payloads from
   both live calls made today.
5. **One-per-engagement writeback redesigned to LAST-decisive-turn-wins**, per explicit user
   decision. ShopDeck's `persist_intelligence_atomic`
   (`business_systems/shopdeck/backend/api/repositories/ndr_queue.py`) allows only ONE
   `ndr_intelligence_results` row per engagement, ever - so submission can't happen per-turn
   anymore. New design:
   - `handle_transcript` now only calls `repo.record_pending_ndr_outcome()` (new method,
     `src/infrastructure/adapters/customer_engagement/repository.py`) on every decisive
     (non-`UNCLEAR`) turn - an unconditional overwrite, so it always reflects the latest
     decisive turn, never the first. UNCLEAR turns never overwrite it.
   - The actual, one-time ShopDeck submission now happens in `handle_session_end`, via new
     helper `_submit_pending_ndr_outcome()`, which reads back whatever was last recorded and
     submits it - guarded by the existing `claim_intelligence_writeback()` atomic
     compare-and-swap (repurposed: still one-per-engagement, just invoked at session-end
     instead of per-turn now).
   - This was a real user-facing bug, not theoretical: a live call today had the customer say
     "day after tomorrow" (decisive), then later, after the bot refused any date but
     tomorrow, say "okay, tomorrow" (also decisive) - first-wins would have recorded the
     wrong, abandoned answer.
6. **The M2M auth token now retries on a 401** (`ShopdeckCemAdapter._authed_request`) -
   previously only the read path did this; the entire write surface had no protection
   against a stale cached token in a long-running process.
7. **Test-debris cleanup script executed successfully for real**
   (`scripts/teardown_test_debris.py --execute`) - verified independently afterward: zero
   synthetic AWBs remain in Postgres, the ~20 real production `ndr_queue` rows are untouched,
   Mongo dropped exactly the expected engagement/event documents. Has a time-based guard
   (protects anything touched in the last 10 minutes) plus a real topological sort over the
   actual FK graph, not a hand-ordered guess.

Full suite (excluding the LLM behavioral harness and two files broken by a pre-existing,
unrelated `pymongo`/`mongomock_motor` import collision): identical 18 pre-existing failures
by name to the established baseline before section 1's regression. After fixing section 1,
re-run and confirm back to that same baseline.

---

## 3. Two physical test calls were placed today - here's exactly what they found

Both calls dialed the operator's own confirmed number, with the shared production queue
verified empty of real eligible items immediately before each seed - no real customer was
ever at risk. Full detail in `docs/claude/physical_gate3_first_two_calls_findings.md`.

**Call 1** ran entirely on a stale server process (up since 4:03 AM, no `--reload`, so none
of today's fixes were loaded into memory). Every known "dumb bot" symptom from the original
task showed up: false "I checked" narration, a fabricated COD amount (₹2500 vs. the real
₹799), a false "I've rescheduled it" claim with no backend action ever taken, the banned
"anything else?" loop. **Fixed** - server restarted, now running with `--reload`
(PID 47135, up since 1:54 PM).

**Call 2**, after the restart, surfaced two bigger findings:

- **The live bot is not running our persona.** `bot_id`/`bot_name` in Exotel's platform
  metadata say `PRIYA` (identical both calls) - but the bot introduced *itself*, in speech,
  as **"सुनेहरी" (Sunehri)**, an evidently older, pre-rename persona (there's a trail of old
  `sunehri_*` files elsewhere in this repo confirming this project used that name before).
  This proves whatever system prompt is actually configured in the **Exotel console** is
  disconnected from `docs/voicebot/bot_persona.txt` entirely - explaining why the "checking"
  narration and a hardcoded "I can only offer tomorrow" line persisted almost verbatim across
  both calls despite session_constants never sending such a constraint. **This cannot be
  fixed from this repository.** It requires opening the Exotel bot-builder console directly
  and confirming/replacing the deployed prompt. ChatGPT (architecture/governance agent)
  recommended, and Claude endorsed: stand up a separate `Bot_Staging` in the console, sync
  `bot_persona.txt` there, verify with a real call, only then promote to production - see
  `.agents/rules/multi-agent-workflow.md` isn't the right file for this, it's not written
  down anywhere yet, so replicate this reasoning if asked.
- **The transcript-extraction bug** described in section 2, item 4 - found by replaying
  Call 2's actual utterances through the classifier once the extraction was fixed.

**Still open, confirmed real, not yet built:**
- No mechanism anywhere extracts a specific date ("10th September") - the classifier only
  pattern-matches generic words like "tomorrow" / "kal". A customer asking for a specific
  future date is currently indistinguishable from one agreeing to "tomorrow."
- Whether Exotel's actual deployed bot uses the same LLM this session's behavioral harness
  tested against (`local-qwen` / Ollama `qwen2.5-coder:7b`, 12/13 pass in
  `tests/test_ndr_behavioral_scenarios.py`) is **unconfirmed**. Given the Sunehri finding,
  it may well be a completely different model, which would mean that harness result says
  nothing about what a real customer actually experiences.

---

## 4. Infrastructure facts worth knowing before touching anything live

- `localhost:5435` is an **SSH tunnel to the real remote VPS Postgres**
  (`aaramhomes@200.234.39.72`), not a disposable local database. It's the same one
  `SHOPDECK_URL` (`https://api-shopdeck.aarambooks.cloud`) serves from. Treat it as shared,
  production-adjacent state.
- `EXOTEL_WEBHOOK_BASE_URL` is an **ngrok tunnel to this local machine**
  (`crave-unlocked-legend.ngrok-free.dev`) - there is no separately deployed VPS Brain
  instance right now. Whatever's running locally on port 8000 is what Exotel actually talks
  to.
- The local server is `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`. It auto-reloads
  on file save now. Confirm it's still alive after any edit
  (`ps aux | grep "uvicorn src.main"`) - a syntax error will kill the reload silently.
- The shared remote `ndr_queue` mixes real production AWBs (~20, numeric-looking) with
  whatever test debris each certification script invents its own prefix for
  (`AWBCERT*`, `TEST_AWB_*`, `AWBGATE3*`, `AWBSELFCALL*` so far). `teardown_test_debris.py`
  hardcodes the prefix list it looks for - a new prefix invented by a future script needs to
  be added there manually or it becomes invisible debris.

---

## 5. The working arrangement, for context

Three agents: Gemini builds, ChatGPT reviews architecture/governance, Claude verifies
code-level correctness against live, unmocked systems. The standing lesson from today,
learned the hard way multiple times (by both Gemini and Claude): a mocked test, a self-report
of "done," or code that merely "agrees with itself" is not evidence something works. Every
significant bug found today - the never-set auth token, the wrong queue_item_id, the wrong
transcript payload shape, the Sunehri persona mismatch - was invisible to every test and
every code review until something was actually run against the real, live system. Keep
doing that before calling anything ready for another physical call.
