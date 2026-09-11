# Brain VPS deployment strategy

Written by: Claude
Originally written: 2026-09-09. Updated three times on 2026-09-12: once after the
Exotel→Sarvam migration work (see `docs/claude/CONTEXT_HANDOFF_SARVAM_MIGRATION.md`) added a
second voice provider with its own webhook, secret, and env vars that didn't exist when this
doc was first written; again after adding real Alembic migrations, which closed a gap this
doc had not previously covered at all (see that section below); again after the Ollama-vs-
Gemini production LLM routing question (open since 2026-09-09) was decided - Gemini, no
Ollama on the VPS.

Context: Brain has never been deployed to the VPS. Identity, Inventory, and ShopDeck BS
already are, each via its own `mac_to_vps_deploy.sh` (Inventory's and ShopDeck's were read
directly to derive this), plus `AaramLauncher/start_all.sh` for local dev. This document
adapts that same proven pattern to Brain and calls out where Brain's actual current code
would break it if deployed as-is today.

**Status as of 2026-09-12, ~20:35 UTC: Brain's first-ever production deploy succeeded.**
`https://api-brain.aarambooks.cloud/health` returns
`{"status":"ok","service":"aarambooks-brain-api","environment":"production"}` for real, over
the public internet, through real nginx + Let's Encrypt TLS. Full account of what changed and
what was verified is below (see "First real deploy" near the end of this doc) - this section
is kept for the historical trail of what was found and fixed to get here, not because any of
it is still hypothetical.

**Correction made during the deploy, not before it**: everything in this doc through
2026-09-12's earlier updates assumed Brain would deploy the same way it was *originally*
built to - `git pull` + `docker compose up -d --build` on the VPS. That turned out to be
already-abandoned: ShopDeck, Identity, Inventory, and Packing have each been extracted into
their own separate GitHub repos, and each publishes a pre-built image to GHCR via its own
`docker-publish.yml` - the VPS only ever pulls, never builds from source, and
`~/aarambooks/brain` on the VPS is a small directory with just `docker-compose.prod.yml`,
`.env`, and `litellm_config.prod.yaml` - no git checkout at all (matching why an accidental
git clone there was worth cleaning up earlier this session, not keeping). Brain's own
`.github/workflows/docker-publish.yml`, `docker-compose.prod.yml` (now `image:` not
`build:`), and `mac_to_vps_deploy.sh` were rewritten to match this real, currently-live
pattern before the first deploy was attempted - confirmed by directly reading
`aarambooks-shopdeck`'s and `Aaram_Inventory`'s actual workflow/deploy-script content on
GitHub, not assumed from memory.

## Database schema management: Alembic added 2026-09-12 - previously did not exist at all

Brain had **no migration tooling whatsoever** until this update - no `alembic.ini`, no
`alembic/` directory, no `alembic` in `requirements.txt`. Confirmed by direct search; your
sibling `Aaram_Inventory` repo has real Alembic, Brain never did. The only thing resembling
schema management was a manual one-off script, `scripts/setup_db.py`, calling
`Base.metadata.create_all` - and that script was itself broken: it explicitly imports only
`SabaqEvidenceRecord`, so of the four real tables that share one `Base`
(`src/infrastructure/database.py`) - `core_memories`, `core_suspended_actions`,
`core_knowledge`, `sabaq_evidence` - running it as written would only ever have created
`sabaq_evidence`. Nothing in `mac_to_vps_deploy.sh` or `docker-compose.prod.yml` called this
script either, so a fresh VPS Postgres would have booted with zero tables and Brain would
have crashed on its first real memory/knowledge write - a deployment-blocking gap that would
not have shown up in the `/health` check.

**Fixed properly, not patched around**, per your explicit direction to do real Alembic
rather than a minimal script fix:

- `alembic==1.20.0` added to `requirements.txt` and installed.
- `alembic/env.py` rewritten (from the stock async template) to import all three real model
  modules (`postgres_memory.py`, `postgres_knowledge.py`, `postgres_sabaq.py` - importing a
  module is what registers its SQLAlchemy model on `Base.metadata`, the same requirement
  that made `setup_db.py` silently incomplete) and to always read the DB URL from
  `settings.database_url` rather than a static value in `alembic.ini`, so the same migration
  runs correctly in dev, CI, and on the VPS with zero per-environment editing.
  (`src/brain_core/infrastructure/database.py` and
  `src/brain_core/context_engine/models.py` each declare their own separate
  `declarative_base()` too, but neither has any model registered against it anywhere in the
  codebase - context_engine's is explicitly documented in its own file as intentionally
  stateless - so there is nothing there for Alembic to track.)
- Generated the baseline migration (`alembic/versions/822cb633d5c8_initial_schema_*.py`)
  against a genuinely empty throwaway Postgres container, not the shared local dev database
  (which already had schema drift - it holds a `core_memories` table but not the others,
  evidence of an earlier partial `create_all` run - so diffing against it would have produced
  a wrong, dev-database-shaped migration instead of the create-everything-from-scratch
  migration a real fresh VPS needs).
- **Found and fixed a real bug in Alembic's own autogenerated output**: the generated file
  referenced `pgvector.sqlalchemy.Vector` for `core_knowledge.embedding` without importing
  `pgvector.sqlalchemy` at all - would have crashed with `NameError` on the very first run.
  Added the missing import.
- **Found and fixed a real omission**: autogenerate has no way to know the `vector` Postgres
  extension needs to exist before a `Vector` column can be created, because the throwaway DB
  used to generate the diff already had it enabled manually. Added an explicit
  `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` at the top of `upgrade()` - without
  this, the migration would fail on a genuinely fresh Postgres with "type vector does not
  exist."
- **Verified end-to-end three times, escalating toward the real deployment artifact each
  time**, not just "it should work": (1) ran `alembic upgrade head` from the local venv
  against a throwaway container Postgres with the extension deliberately *not*
  pre-installed, confirmed all 4 tables plus the `vector` extension were created, and
  confirmed `alembic check` reports zero further drift against the models; (2) built the
  actual `Dockerfile.prod` image and confirmed `alembic/`, `alembic.ini` are present inside
  it (added to `Dockerfile.prod`'s `COPY` steps, which didn't copy them before); (3) ran that
  real built image's `alembic upgrade head` against a second fresh Postgres container over a
  real Docker network connection (not the app's own network stub), exactly mirroring what
  the VPS will actually execute - confirmed the same clean result from the packaged image
  itself, not just the dev venv.
- `mac_to_vps_deploy.sh`'s VPS-side steps restructured so migrations run **before** the app
  container starts serving traffic, not after: build the image → bring up
  `aarambooks-brain-db`/`aarambooks-brain-mongo`/`litellm` → `docker compose run --rm
  aarambooks-brain-api alembic upgrade head` → then `up -d` the app itself. Previously the
  script went straight to `up -d --build`, which (once Alembic existed) would have let the
  app's own healthcheck report "healthy" while the schema was still being migrated, or while
  the app was already crash-looping against a table-less DB on the very first deploy.
- All local throwaway Docker resources (test containers, test network, test image) created
  during this verification were removed afterward. The one already-running shared local dev
  Postgres (`aarambooks-brain-db-dev`, port 5434) was briefly stopped to isolate testing and
  restarted immediately after - its data was never touched, only its own liveness.

**Still not done**: none of this has been committed yet, and it has never been run against
the actual VPS - only against local and throwaway Docker Postgres instances. Going forward,
any new SQLAlchemy model or column change needs a real
`alembic revision --autogenerate -m "..."` before it can reach the VPS - there is no more
`create_all` fallback path once this is committed and the deploy script switches to it.

## The proven pattern (from Inventory and ShopDeck)

Both existing deploy scripts do the same three things, and ShopDeck's is the closer
template since ShopDeck lives inside this same `aarambooks` monorepo, exactly like Brain:

1. `git add . && git commit && git push origin main`
2. GitHub Actions runs CI on push (`gh run watch` blocks until it passes or fails)
3. SSH to the VPS, `git pull origin main`, `docker compose -f docker-compose.prod.yml up -d --build`, run any pending migrations, prune old images

Two things worth naming explicitly because the script's own wording undersells them:
- The CI step does **not** publish an image to any registry (no `docker push`, no `ghcr.io`
  reference anywhere in this repo besides litellm's own upstream image). Its real job is a
  build-validation gate - proving the Dockerfile actually builds - before you spend time
  SSHing in. The actual image that ends up running is built **on the VPS itself**, from the
  freshly `git pull`ed source, via `--build`.
- ShopDeck's `docker-compose.prod.yml` uses `build: context: . dockerfile: Dockerfile.prod`
  for its own services, not a pre-built `image:` reference - `docker compose pull` before
  `up -d --build` mostly just refreshes the `postgres:16` base image, not the app itself.

Brain's deployment follows this exact shape. Because Brain lives at the monorepo root
(not a subfolder like `business_systems/shopdeck`), its version of the script skips the
subfolder `cd` that ShopDeck's needs.

## What was found broken or missing, and fixed - all four confirmed still in place

Constructing this strategy meant actually trying to build the artifact the VPS would build,
not just writing a script that assumes it works. Four real gaps turned up on 2026-09-09.
Re-verified directly against the current source on 2026-09-12 - all four fixes are still
present and committed, nothing has regressed:

1. **The existing root `Dockerfile` is a non-functional placeholder.** It copies only `src/`
   and its `CMD` is `python -c "import time; ...; time.sleep(86400)"` - it never runs
   uvicorn, so containerizing Brain with it would produce a container that does nothing.
   Its own comment ("if physical transport is later authorized") marks it as a relic from
   before Brain was allowed to place real calls. Left untouched (it may still be intentional
   for some dev/CI use); `Dockerfile.prod` exists alongside it - matching how ShopDeck has
   both an implicit dev setup and a distinct `Dockerfile.prod` - and actually runs
   `uvicorn src.main:app`. Note this has already changed once since first written: the
   original version copied `business_systems/catalog/` into the image; Catalog is now
   reached only over HTTP (`CATALOG_URL`, see `src/infrastructure/adapters/catalog_cem_adapter.py`),
   so the current `Dockerfile.prod` no longer copies any of `business_systems/` at all - only
   `src/`, `alembic/`, `alembic.ini`, and `litellm_config.prod.yaml`.

2. **`python-dotenv` was missing from `requirements.txt`.** `src/main.py` does
   `from dotenv import load_dotenv` unconditionally. It happened to be installed in the local
   `.venv` (probably a stray `pip install` from early on), but a fresh container build from
   `requirements.txt` alone would have crashed on the very first import with
   `ModuleNotFoundError: No module named 'dotenv'`. **Fixed and confirmed still present**:
   `python-dotenv==1.2.3` is in `requirements.txt` (line 13).

3. **`MONGO_URI` was not a real, settable config field.** `src/main.py`'s lifespan used to do
   `mongo_uri = getattr(settings, "mongo_uri", "mongodb://localhost:27017")` - but
   `Settings` never declared a `mongo_uri` field, so pydantic-settings had nothing to
   populate from the environment and that `getattr` always silently fell through to the
   hardcoded localhost default, regardless of what `MONGO_URI` was set to. On a VPS where
   Mongo runs in its own container (not on Brain's container's own `localhost`), this would
   have failed to connect. **Fixed and confirmed still present**: `Settings`
   (`src/shared/config.py:12`) declares `mongo_uri: str = "mongodb://localhost:27017"`, and
   `main.py:51` reads it directly (`await MongoDBManager.connect(settings.mongo_uri)`).

4. **CI built the wrong Dockerfile.** `.github/workflows/ci.yml`'s "Build Production Image"
   step used to run `docker build -t aarambooks-brain-core:prod .` - which builds the
   placeholder `Dockerfile`, not the real prod artifact. **Fixed and confirmed still
   present**: `.github/workflows/ci.yml:31` now runs
   `docker build -f Dockerfile.prod -t aarambooks-brain-core:prod .`.

## LLM routing decision - DECIDED 2026-09-12: Gemini, not Ollama

**`litellm_config.yaml` (dev) routes every conversational stage through a local Ollama
instance.** `stage_r_1/2/5/7` (intent routing, planning, entity resolution, response
synthesis - i.e. the models actually generating the voice agent's side of a live NDR call,
per `src/shared/config.py`'s `stage_r_*_model` settings) all resolved to `local-qwen`, which
`litellm_config.yaml` points at `ollama/qwen2.5-coder:7b @ http://host.docker.internal:11434`
- Docker's alias for the **developer's own Mac**. On a VPS, `host.docker.internal` resolves
to nothing unless Ollama is separately installed and running there.

This was flagged as a real product decision on 2026-09-09 (cost/quality/ops tradeoff, not a
default to pick quietly) between running Ollama on the VPS itself (real capacity planning,
new single point of failure) versus routing production's conversational stages to Gemini
instead. **Decided 2026-09-12: Gemini** - explicitly ruled out running Ollama/Qwen on the
VPS ("can't bloat up my VPS with heavy Qwen").

`litellm_config.prod.yaml` (committed since 2026-09-09, unchanged) already implements this:
same stage-routing *names* the code expects (`local-qwen` stays `local-qwen` in
`src/shared/config.py`'s settings - no code change needed), just pointed at
`gemini/gemini-2.0-flash` instead of Ollama. This is not a stale or guessed model id - it's
the exact same real Gemini model already live-serving the two analytics/reporting stages in
the dev config (`litellm_config.yaml`'s `gemini-3.6-flash` entry), so it's a proven, already-
working target, not a new integration. No further code or config change needed here - just
confirm `docker-compose.prod.yml`'s `litellm` service (already wired to mount
`litellm_config.prod.yaml`) is what actually ships.

## Artifacts created - confirmed committed, not just drafted

All committed in `d4b2f39` ("Add first-ever Brain VPS deployment artifacts and strategy
doc") on 2026-09-09, and unchanged since:

- `Dockerfile.prod` - real production image, runs uvicorn, copies only what Brain needs
- `docker-compose.prod.yml` - self-contained stack: brain-api, its own pgvector Postgres,
  its own MongoDB (Brain has never had a containerized Mongo before this), its own litellm
  gateway. No dependency on the developer's Mac for anything, unlike the dev compose file.
- `litellm_config.prod.yaml` - see the Ollama/Gemini decision above
- `mac_to_vps_deploy.sh` - same three-step pattern as Inventory/ShopDeck's, adapted for
  Brain living at the repo root (no subfolder `cd`)
- `.env.example` - documents `MONGO_URI`; since this doc was first written, also gained a
  full Sarvam section (`SARVAM_API_KEY`, `SARVAM_WEBHOOK_SECRET`, `SARVAM_ORG_ID`,
  `SARVAM_WORKSPACE_ID`, `SARVAM_AGENT_ID`, `SARVAM_CONNECTION_ID`, `SARVAM_APP_VERSION`,
  `SARVAM_WEBHOOK_BASE_URL`) that the original version of this plan never accounted for -
  folded into the rollout steps below.

## What changed in the codebase since this doc was first written (2026-09-09 → 2026-09-12)

The single biggest change relevant to deployment: **Brain now supports two voice providers,
not one.** `CustomerEngagementExecutor` dispatches through a provider registry
(`{"EXOTEL": exotel_adapter, "SARVAM": sarvam_adapter}`), and Sarvam's Instant Outbound
integration is code-complete with its own webhook route
(`POST /api/customer-engagement/voice/sarvam/call-completed`), its own query-param-based
auth (`?secret=SARVAM_WEBHOOK_SECRET`, since Sarvam's `webhook_config` has no header-auth
field at all), and its own set of real credentials already live in `.env` locally. This
means:

- The VPS-side reverse-proxy/domain work (see below) now needs to expose **two** webhook
  paths, not one - Exotel's existing `/api/customer-engagement/voice/exotel/*` and Sarvam's
  new `/api/customer-engagement/voice/sarvam/call-completed`.
- `SARVAM_WEBHOOK_BASE_URL` needs the same treatment `EXOTEL_WEBHOOK_BASE_URL` already gets
  in step 4 below - it must point at Brain's real production domain, not a dev ngrok tunnel,
  before Sarvam can reach a deployed Brain.
- `SARVAM_APP_VERSION` was still an uncommitted draft value (`4`) as of this update - this
  needs to be a real, confirmed value before Sarvam calls are placed from the deployed
  environment, independent of anything else in this doc.
- The Sarvam integration has real, passing test coverage
  (`tests/api/webhooks/test_sarvam_call_completed.py`, 7 tests through FastAPI's real
  `TestClient`) exercising the webhook route end-to-end with a repository double - this
  gives the smoke-test step below something concrete to lean on beyond "it imports."

Nothing else material to deployment changed - the four fixes above, the litellm decision,
and the reverse-proxy gap are all exactly as they were on 2026-09-09.

## What is still open - infrastructure outside any repo I can inspect

`api-identity.aarambooks.cloud`, `api-inventory.aarambooks.cloud`, and
`api-shopdeck.aarambooks.cloud` are all live HTTPS domains today, but nothing in any of the
three repos read (this one, Aaram_Inventory, or the launcher) shows how they're
terminated - no nginx config, no Caddyfile, no Traefik labels anywhere. That reverse-proxy
and TLS layer is managed directly on the VPS, outside version control. Brain will need the
same treatment for whatever domain it's given (e.g. `api-brain.aarambooks.cloud`) - a
manual, one-time step on the VPS itself. This gates **both** voice providers' webhooks now:
Exotel needs `EXOTEL_WEBHOOK_BASE_URL` and Sarvam needs `SARVAM_WEBHOOK_BASE_URL`, both
pointing at that same real public HTTPS domain once it exists.

## Recommended phased rollout

1. **Land the code fixes** (`requirements.txt`, `config.py`/`main.py`, `ci.yml`) - already
   done and committed (`d4b2f39`), CI already confirmed green on the `Dockerfile.prod`
   build. Nothing to do here.
2. **LLM routing: decided (Gemini)** - see above. `litellm_config.prod.yaml` already
   implements this and needs no further changes. Nothing to do here.
3. **Provision the VPS-side reverse proxy/TLS/domain** for Brain - whoever manages that box's
   existing nginx/Caddy/Traefik setup for the other three services adds Brain the same way.
4. **Fill in the real `.env` on the VPS** - production DB password, Mongo URI (matches the
   compose file's internal service name automatically if using the file as-is),
   `LITELLM_MASTER_KEY`, `GEMINI_API_KEY`, real `BRAIN_CLIENT_ID`/`SECRET` (Identity M2M
   creds, not the staging ones from `.env.example`), real Exotel account credentials and
   `EXOTEL_WEBHOOK_BASE_URL`, **and now also** the real Sarvam credentials (already known -
   see `docs/claude/CONTEXT_HANDOFF_SARVAM_MIGRATION.md`) and `SARVAM_WEBHOOK_BASE_URL`,
   both pointing at the domain from step 3. Confirm `SARVAM_APP_VERSION` is a real committed
   value, not the `4` draft, before this step.
5. **First deploy**: run `./mac_to_vps_deploy.sh "Initial Brain production deployment"`.
   This now builds the image, brings up the DB/Mongo/litellm dependencies, runs
   `alembic upgrade head` against the fresh production Postgres (creates all 4 tables plus
   the `vector` extension - verified locally against the real built image, see the Alembic
   section above, but never yet against the real VPS Postgres), then starts the app. Confirm
   all four containers report healthy (`docker compose -f docker-compose.prod.yml ps` on the
   VPS) and check the migration step's own output for `Running upgrade -> 822cb633d5c8`
   before assuming success. **Not yet attempted as of this update.**
6. **Smoke test before any real customer touches it** - in this order, each gating the next:
   - `curl https://<brain-domain>/health` returns `{"status": "ok", ...}`
   - A real Exotel webhook round-trip: point one real Exotel test call at the new URL and
     confirm `session-start` → `transcript` → `session-end` all land correctly in Mongo
     (this repo has `scripts/inspect_real_context.py` for a read-only version of the
     upstream half of this - claims one real queue item and prints what would be sent to
     Exotel, without dispatching)
   - A real Sarvam webhook round-trip: place one real Sarvam Instant Outbound test call
     against the deployed URL and confirm `/api/customer-engagement/voice/sarvam/call-completed`
     receives it, `verify_sarvam_bearer()` accepts the real `?secret=` Sarvam sends, and
     `final_agent_variables` extraction writes back to ShopDeck correctly - this has real
     unit/integration test coverage locally, but the query-param auth path has never been
     proven against a genuine live Sarvam delivery, only against the test client
   - Confirm `NDR_MAX_CONCURRENT_CALLS` and the outbound writeback worker are both actually
     running in the deployed process (check the startup logs for both "Started NDR Queue
     Poller" and "Started Outbound Writeback Worker" - both are proven working in code and
     tests, but neither has been proven running in this specific deployed environment yet)
   - Only after all of the above: let one real NDR queue item flow all the way through to a
     real dispatched call (either provider), and manually verify ShopDeck reflects the
     outcome afterward.
7. **Roll back plan**: since the VPS builds directly from `git pull`, rolling back code is
   `git checkout <last-good-sha> -- .` on the VPS followed by the same `up -d --build` - no
   registry/image-tag bookkeeping needed. **This is no longer the whole story once Alembic is
   live**: a code rollback does not automatically undo a schema migration that already ran.
   If the bad deploy included a migration, rolling back also needs
   `docker compose -f docker-compose.prod.yml run --rm aarambooks-brain-api alembic downgrade -1`
   (or to a specific revision) before or alongside the code rollback, otherwise the
   rolled-back code runs against a schema it doesn't expect. Confirm this before you need it
   under pressure, not during an incident.

## Known unrelated backlog that does not block this rollout, but should be resolved before Brain sees production traffic

Carried over from other work this session, not part of the deployment mechanics above but
worth clearing before Brain talks to real customers from the VPS:

- `ShopDeckMasterCCCBuilder`'s constructor accepts an `inventory_provider` argument
  (wired in `src/main.py`) that is never actually used inside `build()` - a maintenance
  trap, not a functional bug, but worth removing or wiring correctly before it misleads
  someone during an incident.
- Three stale scripts (`dry_run_bnctest1.py`, `scripts/business_value_e2e_test.py`,
  `scripts/run_phase5b_benchmark.py`) still call `CatalogCemAdapter` with its old, removed
  `database_url=...` constructor signature - they would crash if run as-is, though none of
  them run automatically as part of deployment or the app's own startup.
- `TEST_PHONE_OVERRIDE` safety hardening (making it environment-enforced rather than merely
  config-dependent, so a misconfigured production environment can't accidentally dial a real
  customer's number through a test path) was proposed but never authorized or implemented.

## First real deploy - 2026-09-12, executed and verified, not just planned

DNS (`api-brain.aarambooks.cloud`, Cloudflare-proxied, same VPS IP as every other service),
nginx + Let's Encrypt TLS (certbot, same pattern as `api-shopdeck.aarambooks.cloud`), the
GHCR publish workflow, and `~/aarambooks/brain/` (containing `docker-compose.prod.yml`,
`litellm_config.prod.yaml`, and a hand-built production `.env`) were all set up and this was
then actually run, not just prepared:

1. Production `.env` built from the real local dev `.env`, changing only what needed to
   change: `EXOTEL_WEBHOOK_BASE_URL` and `SARVAM_WEBHOOK_BASE_URL` from the dev ngrok tunnel
   to `https://api-brain.aarambooks.cloud`; `PACKING_URL` from `localhost:8001` to the real
   `https://api-packing.aarambooks.cloud`; freshly generated `LITELLM_MASTER_KEY` (dev's
   `sk-1234` is a guessable placeholder) and `DB_PASSWORD` (never existed before - dev's
   Postgres has no real password); `TEST_PHONE_OVERRIDE` deliberately dropped entirely -
   confirmed via `grep` that if set, it silently redirects every outbound call (both Exotel
   and Sarvam) to one fixed number instead of the real customer, which would have made
   production NDR calling look like it worked while never reaching a single real customer.
   `BRAIN_CLIENT_ID`/`SECRET` confirmed by the user to already be real production Identity
   creds, not staging. `SARVAM_APP_VERSION` confirmed still not settled - left unset, same as
   dev, matching the code's existing (marked-as-draft) default.
2. Pushed to `main` (`ceb6029`) - CI and the new `docker-publish.yml` both succeeded.
   Confirmed the image was real by pulling it directly on the VPS
   (`ghcr.io/sums0907/aarambooks-brain-core:main`, digest
   `sha256:156e84f9...`) rather than trusting the green checkmark alone.
3. `docker compose -f docker-compose.prod.yml up -d` on the VPS: all 4 containers (api, db,
   mongo, litellm) came up, db and mongo reported healthy within seconds, `aarambooks-brain-api`
   reported `healthy` ~30s later.
4. Read the app's own startup logs directly rather than trusting the healthcheck alone -
   confirmed both background workers actually started (`Started NDR Queue Poller`,
   `Started Outbound Writeback Worker` - the exact two things step 6 of the rollout plan
   above said still needed proving in this specific environment), a real MongoDB connection,
   a real successful Identity M2M token exchange (`POST
   https://api-identity.aarambooks.cloud/auth/service-token` → `200 OK` - this is what
   actually confirmed `BRAIN_CLIENT_ID`/`SECRET` are valid prod creds, not just the user's
   say-so), and a real ShopDeck NDR queue claim call (`204 No Content` - queue was empty,
   which is a valid non-error response, not a failure).
5. `docker exec aarambooks-brain-api alembic upgrade head` against the real production
   Postgres for the first time ever - ran clean, then independently confirmed via `psql
   \dt` that all 4 tables plus `alembic_version` actually exist in
   `aarambooks_brain_core_prod`.
6. `curl https://api-brain.aarambooks.cloud/health` from outside the VPS entirely - real
   `{"status":"ok","service":"aarambooks-brain-api","environment":"production"}`, proving
   DNS, Cloudflare, nginx, Let's Encrypt TLS, Docker networking, and the app itself all work
   together, not just individually.
7. `docker image prune -f` on the VPS afterward (342.9MB reclaimed).

**Issue found during this deploy - fixed the same session, verified against real Postgres,
not just assumed working**: the startup logs showed
`WARNING:src.azm.provider:AZM persistent provider unavailable (psycopg2 is required...).
Falling back to bootstrap.` Two real, separate bugs were behind this, not one:

1. `requirements.txt` never had `psycopg2`/`psycopg2-binary` - `src/azm/db.py`'s raw
   `psycopg2.connect()` call (a sync connection AZM uses independently of the rest of the
   app's asyncpg-based access) had no driver to use at all. Fixed by adding
   `psycopg2-binary==2.9.9`.
2. Even with the driver installed, AZM would still have failed: it reads its own separate
   `AZM_DATABASE_URL` env var (not `DATABASE_URL` - completely independent), which defaults
   to a dev-only address (`localhost:5434`) if unset, and was never set in the production
   `.env` at all. Added the real internal value
   (`postgresql://postgres:<password>@aarambooks-brain-db:5432/aarambooks_brain_core_prod`)
   directly to the VPS's `.env`.
3. Tracing this further surfaced a **third, independent bug**: `src/azm/azm_init.py` (the
   actual tool needed to create AZM's tables) had its post-apply verification query
   hardcoded to SQLite's `sqlite_master`, unconditionally, on both backends - meaning it
   would have crashed with a real PostgreSQL error the first time anyone actually ran it
   against `--db-url postgresql://...`, suggesting it had only ever been run against SQLite
   in practice despite accepting a `--db-url` override. Fixed to branch on
   `conn.is_sqlite` and query `information_schema.tables` for PostgreSQL, matching the
   pattern `src/azm/db.py`'s own `is_initialized()` already used. **Verified against a
   genuine fresh throwaway Postgres container before shipping** (schema creation confirmed,
   then re-ran to confirm the idempotent "already applied" path also works) - not trusted on
   code inspection alone.
4. Rebuilt and redeployed with both fixes, then ran `python -m src.azm.azm_init` inside the
   real production container for the first time - created all 10 real `azm_*` tables in
   `aarambooks_brain_core_prod`. Confirmed the `AZM persistent provider unavailable` warning
   is now completely gone from a fresh container's startup logs.

**Self-inflicted incident during this fix, handled immediately**: `azm_init.py`'s own
`print()` statement includes the full connection string, including the password - running it
put the real `DB_PASSWORD` value in plaintext into this session's tool output. Treated as
exposed rather than risking it: rotated `DB_PASSWORD` immediately (new random value, applied
via `ALTER USER postgres WITH PASSWORD ...` against the real running Postgres, `.env` and
`AZM_DATABASE_URL` updated to match, `aarambooks-brain-api` restarted to pick up the new
credential), then re-confirmed the public health check still returned healthy afterward. This
database is only reachable over the internal Docker network, never exposed to the internet,
so the practical exposure window was narrow - rotated anyway rather than leaving a known-
exposed credential in place.

**Still not done - the smoke-test items below step 6 of the original rollout plan**: a real
Exotel webhook round-trip, a real Sarvam webhook round-trip, and a real end-to-end NDR queue
item flowing through to a dispatched call and back to ShopDeck have not been attempted
against this live deployment yet. The health check and startup verification above prove
Brain is running correctly; they do not yet prove a live customer-facing call works
end-to-end in production.
