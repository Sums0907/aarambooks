# Context handoff — Exotel → Sarvam voice-bot migration

Written by: Claude
Date: 2026-09-11
Why this exists: mid-migration from Exotel to Sarvam AI as the voice-bot provider for NDR
outbound calls. Real code exists and is tested, but the migration is not complete - outbound
dispatch is blocked on missing Sarvam account details. Read this before touching either
voice-bot pipeline.

## TL;DR

- **Exotel is untouched in behavior and still fully live.** Every refactor below was
  verified byte-for-byte behavior-preserving via the existing test suite (51 passed, 5
  pre-existing unrelated failures, confirmed identical via `git stash` diff-testing - not
  assumed).
- **A real, working provider abstraction now exists** so Sarvam (or any future provider)
  plugs in via an adapter, not a rewrite.
- **Sarvam's inbound side (on-start + outcome webhooks) is built and import-verified**, but
  has never received a real Sarvam webhook delivery - payload shapes are best-effort
  reconstructions from incomplete public docs, not confirmed against reality.
- **Design superseded: use Instant Outbound, not Stream Cohort/campaigns.** A dedicated
  single-call API exists (`POST .../api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds`)
  that returns an immediate `attempt_id` and needs no persistent campaign at all - a closer
  match to Brain's per-case dispatch model than the campaign-based approach this doc
  originally described. It also needs no separate on-start hook: variables go directly in
  the creation request (`app_config.agent_variables`), and there's exactly ONE completion
  webhook per call (not two hooks) carrying `status`, `interaction_id`, `failure_reason`,
  the full `interaction_transcript`, and your `webhook_config.metadata` echoed back verbatim.
  **`sarvam_webhooks.py`'s current `/on-start` + `/call-outcome` design needs replacing with
  a single `/call-completed` handler** - not yet done, see "What's NOT built yet."
- **`SarvamVoiceBotAdapter.dispatch_call()` does not exist yet, but every config value it
  needs is now known and verified loaded** in `src/shared/config.py`: `sarvam_org_id`,
  `sarvam_workspace_id`, `sarvam_agent_id` (`Conversatio-eb70cc88-1de5`), `sarvam_connection_id`
  (`13179346-34-3b0ee88e-dd86`), `sarvam_phone_number` (`+918065383367`), `sarvam_api_key`
  (a Voice-Agents-specific key, confirmed separate from standard Sarvam TTS/STT keys). Real
  auth header confirmed by the user directly from their dashboard: `X-API-Key`, not
  `API-Subscription-Key` as earlier guessed. **The only missing value is `app_version`**
  (integer, required by Instant Outbound - check the agent's Versioning tab, likely `1`).
- **Telephony decision already made**: rent numbers directly from Sarvam, no Exotel/Twilio
  dependency underneath. Full break from Exotel is the intent.

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

**Config status - all known, one is a placeholder pending a real commit:**
- ✅ `org_id`, `workspace_id`, `agent_id` (`Conversatio-eb70cc88-1de5`), `connection_id`
  (`13179346-34-3b0ee88e-dd86`), `phone_number` (`+918065383367`), `api_key` - all live and
  verified loaded in `src/shared/config.py`.
- ⚠️ `app_version = 4` is set, but **this is currently a DRAFT** ("in-progress edits, not yet
  live" per Sarvam's own docs) - the user is still editing it, not yet committed. Do not run
  a real test call against this until it's committed to a real version number; update
  `sarvam_app_version` then. Unconfirmed whether Instant Outbound can even target a draft.
- ❌ `SARVAM_WEBHOOK_SECRET` still empty - needs a real value once the completion-webhook
  auth mechanism is confirmed (see `verify_sarvam_bearer()`'s docstring).

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

## Uncommitted work in this repo right now (not part of this migration, don't touch)

`docs/voicebot/aaram_homes_payment_terminology.txt` shows as modified in `git status` but was
not touched by any of the work in this handoff - almost certainly Gemini's concurrent edit
(per the standing multi-agent working arrangement on this repo). Left exactly as found.

## Recommended next steps, in order

1. ~~Get `org_id`, `workspace_id`, `agent_id`, `connection_id`, `phone_number`, `api_key`~~ -
   **All done**, live and verified loaded in `src/shared/config.py`.
2. ~~Write `SarvamVoiceBotAdapter.dispatch_call()`~~ - **Done**, written and import-verified,
   never called against the real API.
3. ~~Rewrite `sarvam_webhooks.py`~~ - **Done**. Single `/call-completed` handler, old
   `/on-start` + `/call-outcome` design and `map_sarvam_reschedule_decision()` removed.
4. **Commit the agent's draft version** (currently `4`, in-progress) once its edits are
   finished, and update `sarvam_app_version` to the real committed number. Do not skip this
   to test faster - the docs' described workflow is commit-then-test, and it's unconfirmed
   whether a draft is even callable.
5. Set a real `SARVAM_WEBHOOK_SECRET` value and set `SARVAM_WEBHOOK_BASE_URL` to a reachable
   tunnel/domain (needed for `webhook_config.url` - without it, `SarvamVoiceBotAdapter`
   dispatches with no way to learn the outcome, logged as a warning but not blocked).
6. Place one real test call end-to-end - this answers the remaining open questions (real
   latency, exact completion webhook payload shape matching what's coded, whether
   `agent_variables` keys must exactly match the agent's configured variables) with actual
   evidence, not assumption. Check what actually lands in Brain's database and ShopDeck's
   queue from that call.
7. Full production system-prompt port (not the condensed test version in
   `SARVAM_MOCK_TEST_SETUP.md`) once the above is proven end-to-end.
8. Only after full parallel verification: any decision to move real production call traffic
   off Exotel - not a hard cutover on day one, given this is live customer-facing calling.
