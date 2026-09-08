# TODO — road to Physical Gate 3

Author: Claude
Date: 2026-09-08
Purpose: one consolidated, sequenced list of everything still open across today's session.
Ordered so each phase is a real prerequisite for the next one, not just a priority ranking.
Nothing here should be treated as done until the specific verification step next to it has
actually been run - that's been the pattern of every real bug found today.

---

## Phase 0 — stop the bleeding: get today's work into git

Nothing from today is committed. `git log` still shows the last real commit as "Add
certification script," from before this session. Nineteen files are modified and a dozen new
ones are untracked, all sitting only in the working tree.

- [ ] Review `git status` and stage today's real changes (exclude scratch scripts like
      `dump_transcript.py` / `format_transcript.py` / `parse_transcript.py` if they're just
      throwaway debugging tools, not something to keep long-term).
- [ ] Commit with a message that captures the actual scope (mission contract, writeback
      redesign, last-turn-wins, debris cleanup, greeting fixes).
- [ ] Do this **now**, before anything below - a crash, a bad edit, or a lost session
      shouldn't be able to erase a full day of verified work again.

---

## Phase 1 — fix what's confirmed broken in the console prompt itself — DONE 2026-09-08

These are grounded in the actual pasted console text, not guesses. All console-side; nothing
here is a code change in this repo.

- [x] **Remove every "Sunehri" reference from the console prompt**, replacing with "Priya"
      consistently - including the literal suggested opening line
      ("नमस्ते, मैं सुनेहरी..." → "...मैं प्रिया..."). Confirmed root cause of the
      self-identification mismatch: the model is handed a line containing "Sunehri" as
      example text to actually say. DONE: the full corrected `bot_persona.txt` (no Sunehri
      anywhere) was pasted into the console's Identity block, replacing whatever was there
      before, and Save was clicked.
- [x] **Sync the "STRICT INSTRUCTIONS" framing into the console prompt.** Confirmed missing:
      the deployed text had no section telling the model that dynamically-injected
      `instruction_*` fields (like `instruction_lookup_rule`, `instruction_no_stalling`) are
      binding rules. DONE: carried in automatically by the same full-file Identity paste
      above, since `bot_persona.txt` contains this section (committed to this repo in
      `65ee876`).
- [x] **Fixed the separate "Greeting Message" field** (found during this phase, not on the
      original list): it held a static, English, pushy line
      ("Would you like to confirm receipt or cancel your order?") that skipped straight to a
      binary decision with no consent step and no Hindi language-choice ask - exactly the
      anti-pattern the whole redesign targets. Replaced with the Hindi language-choice
      opening from `bot_persona.txt:125`. Open question for Phase 6: real Call 2 evidence
      suggests this field (and even the webhook's own dynamic `greeting_message.text`) may
      not be what's literally spoken - the model may generate its own opening from Identity
      regardless. Verify on the next real call which source the actual opening line matches.
- [x] **Confirm what LLM/ASR the console bot is actually configured to run.** CONFIRMED
      2026-09-08 via Configuration tab screenshot: LLM is `Gemma4-Gateway-Exotel` (Google's
      Gemma family, gatewayed by Exotel - NOT `local-qwen`, which is what
      `tests/test_ndr_behavioral_scenarios.py` actually tests against). STT is
      `Smallest AI · Pulse` (config preset `Exotel's Smallest`). Consequence: the behavioral
      harness's 12/13 result answers a question about a different model than the one talking
      to real customers - it needs to be re-run against the real model (if the console
      supports pointing an offline harness at it) or explicitly retired as non-evidence.
      Working hypothesis, not yet proven: Gemma is a smaller open-weight model, plausibly
      weaker than a frontier model at obeying the long, dense STRICT INSTRUCTIONS block under
      real conversational pressure - a real, testable explanation for the pushy/narrating
      behavior seen on both live calls, independent of whatever the prompt text says.
- [x] **Checked the Configuration tab's "Specialization Prompts."** Both are generic Exotel
      stock templates, not yet customized for Aaram Homes/Priya - unclear whether `0/1` means
      inactive or "unconfigured default is live"; check for an enable/disable toggle before
      relying on either.
      - `NumberCapturing`: TTS **output formatting only** (how to speak phone numbers, IDs,
        currency amounts aloud digit-by-digit vs. naturally). Does NOT extract dates/numbers
        from customer speech - Phase 2's date-extraction gap is still completely unbuilt,
        on both the Exotel side and in `reply_parser.py`. Unrelated to the Call 1 fabricated
        COD amount (₹2500 vs real ₹799) - that was hallucinated data, which this module
        cannot fix since it only formats numbers already known to be correct.
      - `LanguageSwitching`: conflicts with `bot_persona.txt` on one point - its example
        ("Sure, I will continue in English now") is exactly the announce-the-switch phrasing
        `bot_persona.txt` explicitly bans ("Do NOT say: 'I'll continue in Hindi.' Simply
        continue naturally."). If this module is actually live, either disable it (Identity
        already covers language switching more precisely for this use case) or rewrite its
        confirmation example to match the "switch silently" rule.

---

## Phase 2 — decide the open design questions before building around them

- [ ] **Decide the "only tomorrow" delivery-option question.** Confirmed: the console
      prompt's tomorrow-only rule is *conditional* ("if the current context says only
      tomorrow is allowed..."), not a hardcoded default - and nothing this repo currently
      sends in `session_constants` supplies any explicit delivery-option data at all. Two
      real options, pick one deliberately:
      (a) build real delivery-window data into `session_constants` (needs Phase 3's
      `ndr_context` investigation first), or
      (b) explicitly decide tomorrow-only is an accepted, deliberate V1 constraint and send
      it as one on purpose, rather than letting the model default into it silently.
- [ ] **Decide the date-extraction question** (the "day after tomorrow" / "10th September"
      gap). Nothing in `reply_parser.py`'s classifier extracts a specific date beyond generic
      "tomorrow" pattern matching - confirmed by replaying a real call where the customer
      asked for a different date and the system had no way to represent that. Either build
      real date extraction, or explicitly accept "any non-tomorrow date collapses to
      UNCLEAR or a generic RESCHEDULE" as a stated V1 limitation. Don't leave this as an
      accidental gap - make it a decision either way.

---

## Phase 3 — one concrete investigation, cheap to do, informs Phase 2

- [ ] **Check whether ShopDeck's `ndr_context` (returned in `NDRClaimResponse.ndr_context`
      at claim time) ever reaches `session_constants`.** Current belief: it does not - only
      the CCC projection (`call_context`) feeds `build_session_constants()`, and
      `ndr_context` is a separate, richer object from the claim response that appears to be
      fetched and then dropped. If it contains real delivery-window/date data, wiring it in
      may directly resolve Phase 2's "only tomorrow" question with real data instead of a
      guess either way.

---

## Phase 4 — build whatever Phase 2 decided needs building

- [ ] If Phase 2 chose to build real delivery-option data: wire it from `ndr_context`
      (Phase 3) or wherever it actually lives, into `session_constants`, with a test proving
      it reaches the payload (same pattern as the existing mission-field allow-list test in
      `tests/test_ndr_mission_contracts.py`).
- [ ] If Phase 2 chose to build real date extraction: extend `reply_parser.py`'s classifier
      (or replace the heuristic with the existing but currently-unused LLM-based
      `CustomerReplyParser` / `ParsedOutcome.reschedule_date`) and wire the extracted date
      into the `pending_ndr_outcome` recorded by `handle_transcript` and the payload
      submitted by `_submit_pending_ndr_outcome`.
- [ ] Re-run the full test suite after either change; confirm back at the established
      18-failed/404-passed baseline (unrelated pre-existing failures only).

---

## Phase 5 — isolate testing from production before the next real call - DECIDED 2026-09-08

- [x] **Decided against a separate `Bot_Staging` bot, by explicit user choice.** Exotel has no
      formal staging/production distinction of its own, so a second bot would need every
      future console edit (persona, instructions, etc.) applied twice to stay in sync -
      exactly the same failure mode already found once this session (the console's persona
      silently drifting out of sync with `docs/voicebot/bot_persona.txt`). Rather than
      recreate that risk deliberately, testing continues against the single existing
      production bot, protected by the same manual protocol already used for both physical
      test calls today: verify the shared queue has zero real eligible items, confirm the
      test phone number explicitly, confirm the server is running fresh code before
      dispatching.
- [x] **Built the switch mechanism anyway, left dormant.** `exotel_voicebot_flow_url_staging`
      (`src/shared/config.py`), `ExotelVoiceBotAdapter(use_staging=...)`
      (`exotel_adapter.py` - raises immediately if staging is requested but not configured,
      never silently falls back to production), and `--staging` on
      `scripts/run_one_real_call.py`. Defaults to empty/unused - available without rework if
      a *temporary* staging bot is ever wanted for one specific risky change.
- [ ] Every real test call still goes through the manual safety protocol above - this has not
      changed and does not get relaxed just because bot-level isolation was declined.

---

## Phase 6 — the actual empirical gate (nothing above substitutes for this)

- [ ] Re-verify the shared `ndr_queue` has zero real eligible items before seeding anything
      (same check used both times today - takes 30 seconds, has caught nothing wrong yet,
      keep doing it anyway).
- [ ] Seed one test item, place one real call against `Bot_Staging` specifically.
- [ ] Pull the transcript and check, explicitly, against this checklist - not vibes:
      - [ ] Opens correctly (states the reason or the console's own short-opening design,
            whichever was decided; asks consent, not a date, if using our greeting design -
            or confirm the console's "ask language first" design is the accepted one instead)
      - [ ] No self-identification as anything but Priya
      - [ ] No "checking / let me see / one moment" narration
      - [ ] No repeated reschedule push after answering an unrelated question (the exact
            worked example already in the console prompt - test whether it's actually obeyed
            now, since it wasn't in either call today despite being explicitly written down)
      - [ ] No fabricated facts (amount, color, etc.) - matches real seeded data exactly
      - [ ] `ndr_queue.queue_status` reaches `action_ready` and `ndr_intelligence_results`
            has the correct, final (last-turn-wins) row after the call ends
- [ ] If any box fails, that's real signal about whether the console-side fix actually
      worked, or whether Phase 1's harder problem (instruction-adherence under a long dense
      prompt, independent of what the text says) is the real limiter. Don't re-run the same
      test hoping for a different result without changing something first.

---

## Phase 7 — promotion, and one more check specifically on production

- [ ] Only after Phase 6 passes cleanly: promote `Bot_Staging` to `Bot_Production` (or
      repoint the real flow), per whatever the console's versioning/traffic-percentage
      mechanism requires.
- [ ] Place **one more** real call against the production configuration specifically.
      Promotion itself can shift traffic percentages or publish state - don't assume staging
      passing means production is identical without checking once, directly.
- [ ] Only now, refresh `docs/03-intelligence-domains/ndr-intelligence/GATE3-PASS-MASTER.md`
      (and its duplicate under `docs/09-decisions/`) to reflect reality - and only if every
      box in Phase 6 and this phase is genuinely true. That document has already recommended
      "YES" once while its own listed prerequisite was unmet; don't repeat that.

---

## Architecture decision, 2026-09-08 — Brain must never hold ShopDeck's Postgres credential

Stated by the user as the governing principle: **AaramIdentity decides whether Brain may call
ShopDeck BS; ShopDeck BS decides what that API call can do and uses its own database credential
to reach PostgreSQL. Brain should never need ShopDeck's PostgreSQL user.** Any Brain-side code
connecting directly to `shopdeck_bs_prod` with the `postgres` superuser credential (found in
`business_systems/shopdeck/.env`) violates this - it bypasses AaramIdentity's authorization and
ShopDeck BS's own API-level permission checks (`SHOPDECK_VIEW`/`SHOPDECK_EDIT` in
`business_systems/shopdeck/backend/api/auth.py`) entirely, going straight to the database engine.

- [x] **Ten dead, unreferenced root-level debug scripts removed** (`test_e2e_cert2.py`,
      `query_real_awb.py`, `test_db.py`, `db_audit.py`, `db_cert.py`, `dump_transcript.py`,
      `check_ndrs.py`, `test_e2e_cert.py`, `copy_db.py`, `query_real_awb2.py`) - all connected
      directly to ShopDeck's Postgres with the superuser credential, none referenced by any
      other code, served no ongoing purpose.
- [x] **Explicit, deliberate exception, by user decision:** the four certification scripts in
      `scripts/` (`certify_gate2.py`, `certify_gate3_writeback.py`, `inspect_debris.py`,
      `teardown_test_debris.py`) keep their direct Postgres connections as-is, untouched. These
      are pre-deployment verification/ops tooling, not production runtime code - they seed and
      inspect synthetic test data that ShopDeck's business API was never designed to expose
      (there is no "create a fake test order" endpoint, nor should there be one in production).
      User's explicit call: this is a narrow, named, visible exception to the principle above,
      not a silent one - do not extend this pattern to any new script without the same
      deliberate sign-off, and do not treat this note as license to add more direct-DB scripts.
- [ ] **Still open:** any future need for ShopDeck-owned data that Brain's production code
      (not test tooling) requires - e.g. the courier/attempt/RTO timing data from
      `ndr_action_log` that motivated this whole investigation - must be served by a real
      ShopDeck BS API endpoint (using ShopDeck's own internal DB credential internally, gated
      by AaramIdentity like every other cross-service call), never by handing Brain a database
      credential of any kind, scoped or not. The one-off RTO-timing analysis itself should be
      run by whoever operates ShopDeck's own environment directly, with only the resulting
      numbers - not database access - handed back to Brain/the user.

---

## Independent / lower-urgency, can happen anytime in parallel

- [ ] **Knowledge Base upload** for Aaram Homes tier-3 FAQ/policy content in the Exotel
      console (return policy, exchange policy, general company questions) - `bot_persona.txt`
      already defines this as a fallback tier, but nothing's been uploaded, which is a
      plausible reason "return policy" questions got vague answers on real calls.
- [ ] **Debris-prefix hygiene**: `teardown_test_debris.py` matches a hardcoded list of AWB
      prefixes (`AWBCERT`, `TEST_AWB_`, `AWBGATE3`, now also `AWBSELFCALL`). Every new
      certification script that invents its own prefix becomes invisible debris until someone
      remembers to add it to that list. Worth a single shared constant
      (e.g. `TEST_AWB_PREFIX = "ZTEST_"`) that every future test/certification script is
      required to use, instead of continuing to grow this list by hand.
- [ ] **Remove `DummyAction`/`DummyUnderstanding` scaffolding** still embedded inline in
      `src/workers/ndr_queue_poller.py`'s production dispatch path - flagged as debt earlier
      in the session, never actually removed. Not urgent, but it's test scaffolding sitting
      in a real code path.
- [ ] **Remove `settings.shopdeck_token`** from `src/shared/config.py` - dead config, never
      actually used anywhere since the writeback was fixed to use the real M2M auth flow
      instead.
