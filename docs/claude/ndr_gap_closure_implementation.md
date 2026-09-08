# NDR gap-closure implementation report

Author: Claude (implementation)
Date: 2026-09-08
Scope: the four items in Gemini's revised gap-closure plan.

## Item 4 — hardcoded phone: fixed

`DummyAction.parameters["customer_phone"]` no longer starts as `"1234567890"`. It is
confirmed NOT dead code first: `exotel_adapter.py:37` reads it as the literal `"From"` number
on the real outbound Exotel call. Fixed by populating it, and the identical hardcoded value
in the stored `call_context`, from `ccc.customer_profile.phone` immediately after
`ccc_builder.build()` hydrates it - with a guard that refuses to dispatch if hydration
somehow produced no phone at all.

## Item 3 — de-mock `certify_gate2.py`: done, verified against the real endpoint

Seeded `order_line_items` and `customer_info` for the synthetic AWB, matching the tables the
real hydration path (`ShopdeckCemAdapter` -> ShopDeck's `GET /api/v1/ndr/{awb_no}` ->
`NDRService.get_shipment_ndr_context`) actually reads, as identified in the prior plan review.
`DummyCCC` removed entirely.

**Important correction to how this was framed:** `localhost:5435` (where `certify_gate2.py`
connects) is not a disposable local database - it is an SSH tunnel
(`ssh -fNT -L 5435:172.21.0.2:5432 aaramhomes@200.234.39.72`) into the same remote VPS
Postgres that backs the live `SHOPDECK_URL` (`https://api-shopdeck.aarambooks.cloud`). This
script has always written to shared, remote state; that predates this work. Worth knowing
because "run the local certification" is not actually local.

**A real defect surfaced and was root-caused via VPS logs** (with explicit permission,
since SSH access to shared infrastructure is exactly the kind of action that should require
sign-off): the first corrected seed still hit a `500` on ShopDeck's side. The traceback
(`docker logs shopdeck-api` on the VPS) showed:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for NDRShipmentContext
ofd_count
  Input should be a valid integer [type=int_type, input_value=None, input_type=NoneType]
```

`ofd_count` was left `NULL`. `NDRShipmentContext.ofd_count: int = Field(0, ...)` has a
default, but Pydantic only applies a default when the key is *absent* from the input -
`report_data` comes from `dict(asyncpg.Record)`, so a `NULL` column is a present key with
value `None`, and a non-`Optional[int]` field rejects `None` even with a default set. Fixed
by seeding `ofd_count = 0` explicitly, with a comment on this exact gotcha so nobody
re-introduces it by trusting a schema default for a nullable column.

**Verified against the real ShopDeck endpoint**, not just locally:
`GET https://api-shopdeck.aarambooks.cloud/api/v1/ndr/AWBCERT05A3B8D8` -> `200`, full
`NDRShipmentContext` returned. Then verified through the Brain's own `ccc_builder.build()`
against that same AWB: phone, COD amount, product name, and `mission.why_this_call` all
hydrated correctly. `DummyCCC` removal is proven, not just asserted.

### A structural problem this surfaced, left for you to decide

The shared remote NDR queue has an accumulating backlog: 9 stale eligible items when this
session started (oldest since Sep 7), one recurring `TEST_AWB_cc177c21` fixture claimed and
abandoned 4+ times across sessions, now 10 after this session's runs. `claim_next_eligible()`
claims oldest-first, so a freshly-seeded, correctly-formed certification row sits behind that
backlog and is never actually exercised by `process_next_item()` until the backlog clears one
failed claim at a time. This session's run did clear one item (`TEST_AWB_cc177c21` finally
hit `permanently_failed` after its `max_claim_attempts` was reached), but the backlog is net
growing, not shrinking, because every certification run adds at least one new row and nothing
retires old ones proactively.

I did not clean this up myself - deciding what shared queue state is safe to discard is your
call, not a code-correctness question. Two honest options: add a teardown step to
`certify_gate2.py` that deletes only the rows it itself seeded (it already knows every
`qid` it created), or accept that gate runs against this queue will keep getting slower as
debris accumulates.

**Separately, and unrelated to anything in this work:** ShopDeck's own
`PATCH /api/v1/ndr/queue/{id}/status` endpoint threw a `500` the first time this session tried
to mark the stale item `failed_retryable` (it succeeded on a later attempt once retried). That
bug lives in `business_systems/shopdeck/`, a different service - flagged, not touched.

## Item 1 — LLM behavioral harness: built, run, one real finding

`tests/test_ndr_behavioral_scenarios.py`, all 13 scenarios (A-M). Explicitly advisory, skipped
automatically if the LiteLLM gateway isn't reachable, never gates anything.

Before writing it, extracted `build_session_constants()` out of
`src/api/webhooks/exotel_webhooks.py:handle_session_start` into a standalone function. Both
the production webhook and this harness now call the exact same function - the harness
evaluates the real payload production sends, not a hand-rolled approximation of it. (This
also meant updating one existing gating test,
`test_every_mission_field_reaches_the_exotel_session_constants_allow_list`, to check the
new function's source instead of the webhook handler's - a mechanical follow-on, not a
behavior change.)

Persona: `docs/voicebot/bot_persona.txt`, read byte-for-byte, never edited or excerpted. One
disclosed assumption: the file has no explicit `{{placeholder}}` for `session_constants`, so
how Exotel's actual runtime injects it isn't visible from this repo. The harness appends it as
a delimited "CURRENT CALL CONTEXT" block on the same system prompt - a reasonable
approximation, stated as an assumption in the file's docstring rather than presented as fact.

Scoring uses a second LLM call (temperature 0) as a judge against each scenario's specific
criteria, returning a parsed JSON verdict. This is weaker evidence than a deterministic
assertion - a pass means "plausible," not "proven."

**Real result on first run, against the currently configured model
(`local-qwen` / Ollama `qwen2.5-coder:7b`): 12 of 13 scenarios passed.** Scenario A failed
honestly rather than being tuned to pass: customer said "Haan, bataiye kya hua" ("yes, tell me
what happened") - the correct behavior is for Priya to now explain the delivery failure. The
model instead replied "जी, एक बार फिर बताएं। क्या हुआ?" ("please tell me again, what
happened?") - deflecting the question back to the customer instead of continuing the mission
narrative herself. Worth noting this model is a code-completion model, not one obviously
suited to nuanced Hindi conversational roleplay, which may be a confound distinct from
whether the mission/prompt design itself is sound - scenarios B through M, comparably or more
demanding, all passed with the identical prompt and persona. This is reported as-is, not
explained away; rerunning against a different configured model (`gemini-3.6-flash` is already
in `litellm_config.yaml`) would help separate a model-capability issue from a prompt-design
issue.

## Item 2 — ShopDeck writeback E2E: a second real auth bug found and fixed

Before this could be tested, found that my own earlier writeback fix (from the prior
implementation round) authenticated with `settings.shopdeck_token` - a setting that is
declared in `src/shared/config.py` but never set anywhere (`.env` has no `SHOPDECK_TOKEN`).
Every real writeback attempt would have failed authentication silently the same way the
original `"dummy_token"` did, just with a different-looking placeholder.

The correct mechanism already exists: ShopDeck writes authenticate via Aaram Identity's
M2M service-token flow (`ShopdeckCemAdapter._get_auth_header` /
`_get_shopdeck_token`, cached in-process), and `ShopdeckCemAdapter.submit_intelligence()`
already implements this call correctly. The webhook now imports the shared `shopdeck_cem`
singleton from `src.main` and calls `submit_intelligence()` directly instead of re-deriving
auth by hand. `httpx`/`os` imports in the webhook module, now unused, were removed.

This changed the call shape the two existing e2e tests mock against: `submit_intelligence()`
makes two real HTTP calls under the hood (fetch/cache the M2M token, then the actual POST),
where the previous hand-rolled version made one. Both tests
(`test_ndr_queue_e2e_4_items`, `test_outcome_unknown_recovery`) asserted
`mock_post.assert_called_once()`, which is no longer true - not because the code regressed,
but because it now goes through a more correct, real auth path. Fixed by having both tests
search `call_args_list` for the specific `intelligence_results` call rather than assuming
total call count; the payload assertions themselves (`recommended_action`, `customer_intent`,
`diagnosis`, `awb_no`, `result_id` format) are unchanged and still pass.

**Not yet verified against the actual live endpoint with a real POST** (as opposed to a
Pydantic/schema-level check) - that's the natural next step, and now that auth is pointed at
the mechanism that's already proven to work elsewhere in this codebase (the hydration path
uses the identical `_get_auth_header()`), I'd expect it to succeed, but "I'd expect" is not
the same as verified. Flagging rather than claiming it.

## Test evidence

```
tests/                          (excluding the LLM harness): 18 failed, 432 passed
```
Identical failure count and identical failing tests to the baseline established in the prior
implementation round - confirmed by name, not just by count. Nothing in this session's work
introduced a new deterministic failure.

`tests/test_ndr_mission_contracts.py`, `tests/api/webhooks/`, `tests/test_ndr_queue_e2e_local.py`:
53/53 passed after the `build_session_constants` refactor and the writeback auth fix.

`tests/test_ndr_behavioral_scenarios.py`: 12/13 passed (real LLM run, documented above) -
advisory, not part of the 18/432 gating figures.

## What's still open

- The queue backlog problem (above) - a decision for you, not a code fix I made unilaterally.
- Item 2's live-endpoint POST verification, one step short of done.
- Everything already listed as open in the prior implementation report: no server-side
  conversation-state enforcement in V1 (mission retention is prompt adherence only), and no
  physical call was made.
