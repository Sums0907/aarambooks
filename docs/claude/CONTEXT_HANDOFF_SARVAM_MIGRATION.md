# Context handoff — Exotel → Sarvam voice-bot migration

Written by: Claude
Originally written: 2026-09-11. Updated 2026-09-13 - Sarvam is no longer "mid-migration,
blocked on missing details." It is code-complete, deployed to production, and the VPS's own
live poller is configured to dispatch every new NDR through Sarvam automatically. What's
actually still open now is narrower and described in the new section below - read that first
if you're picking this up fresh, the sections after it are the original build history.

## TL;DR (current, as of 2026-09-13)

- **Sarvam is live in production**, not a draft. `DEFAULT_VOICE_PROVIDER=SARVAM` is set on
  the VPS - real NDR dispatches go through Sarvam automatically via the normal poller, no
  manual script needed. `sarvam_app_version=23` is the real, user-confirmed committed value
  (no longer the draft `4` described further down this doc).
- **Exotel still exists and still works** (nothing about it was removed), but it is no longer
  the default - `default_voice_provider` is a real config value now
  (`src/shared/config.py`/`executor.py`), not a hardcoded constant, specifically so this can
  be flipped without a code change again in the future.
- **A real end-to-end Sarvam call has still never actually completed** - not because
  anything is broken in Brain, but because ShopDeck's production NDR queue has been
  genuinely empty of eligible items every time it's been checked (see "The queue
  investigation" below for the full, verified reason why).
- **Three real bugs were found and fixed since this doc was first written** - see "Bugs
  found and fixed" below - a name-corruption bug, a missing per-call instruction variable,
  and the `default_voice_provider` gap itself.
- **Do not run more manual one-off test scripts for this.** The VPS's own poller is already
  correctly configured and running continuously - the only thing blocking a real test is
  ShopDeck's queue having nothing eligible, not anything Brain needs done to it again.

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

### The queue investigation - why a real Sarvam call still hasn't completed

Not a Brain bug. Traced end to end, with real evidence at every step, together with the
ShopDeck-side agent:

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

## Recommended next steps, in order (updated 2026-09-13)

1. ~~Get `org_id`, `workspace_id`, `agent_id`, `connection_id`, `phone_number`, `api_key`~~ -
   **Done.**
2. ~~Write `SarvamVoiceBotAdapter.dispatch_call()`~~ - **Done.**
3. ~~Rewrite `sarvam_webhooks.py`~~ - **Done.**
4. ~~Commit the agent's draft version and update `sarvam_app_version`~~ - **Done**, real
   value `23`.
5. ~~Set a real `SARVAM_WEBHOOK_SECRET` and `SARVAM_WEBHOOK_BASE_URL`~~ - **Done.**
6. ~~Fix `default_voice_provider` so real dispatches actually go to Sarvam~~ - **Done**,
   `DEFAULT_VOICE_PROVIDER=SARVAM` live on the VPS as of 2026-09-13.
7. **Still open: let one real, genuinely eligible NDR actually reach the VPS's poller and
   complete a real Sarvam call.** Nothing further needs doing on Brain's side for this -
   the poller is running, correctly configured, and will pick up the next eligible item on
   its own. This is now blocked purely on ShopDeck's enrollment producing a fresh eligible
   item (see "The queue investigation" above), not on anything in this repo. When it does
   happen, check: real call latency, whether the completion webhook payload matches what
   `sarvam_webhooks.py` expects, and whether `agent_variables` keys still match the agent's
   currently-configured variable list (the agent has been edited since this was last
   confirmed).
8. Full production system-prompt port (not the condensed test version in
   `SARVAM_MOCK_TEST_SETUP.md`) once step 7 is proven end-to-end.
9. Only after full parallel verification: any decision to move real production call traffic
   off Exotel - not a hard cutover on day one, given this is live customer-facing calling.
