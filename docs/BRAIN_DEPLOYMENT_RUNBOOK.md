# Brain deployment runbook

Written by: Claude. Last verified against the real live VPS: 2026-09-12.

This is a reference document, not a narrative - it describes the deployment as it actually
works today, verified step by step against the real VPS, GitHub, and GHCR, not as originally
planned. For the history of what was found broken and fixed to get here, see
`docs/claude/DEPLOYMENT_STRATEGY_BRAIN_VPS.md`. If you are an AI agent picking up deployment
work on Brain with no other context, this document should be enough on its own.

**Read this whole document before running any command in it.** Several steps depend on
decisions made in earlier steps (secrets generated once, DNS created once). Re-running an
early step against an already-live deployment can be destructive (e.g. regenerating
`DB_PASSWORD` without updating the live database will lock Brain out of its own data).

---

## 1. What Brain is, in this deployment's terms

Brain is a FastAPI app (`src/main.py`) that:
- Talks to Identity, Inventory, ShopDeck, and (eventually) Catalog and Packing as
  cross-service HTTP clients.
- Places outbound NDR recovery calls through Exotel and/or Sarvam (two interchangeable voice
  providers behind one adapter interface).
- Persists to two databases of its own: a PostgreSQL instance (pgvector-enabled) and a
  MongoDB instance.
- Routes its own LLM calls through a dedicated LiteLLM gateway container, not directly to any
  model provider.

It runs as 4 containers on the VPS: `aarambooks-brain-api`, `aarambooks-brain-db`,
`aarambooks-brain-mongo`, `litellm-brain-prod`. There are no other Brain-owned containers -
its two background workers (NDR Queue Poller, Outbound Writeback Worker) run as asyncio tasks
inside the API container's own event loop, not as separate containers, and are not expected
to ever become separate containers.

## 2. The deployment model - GHCR images only, never git on the VPS

**Do not assume Brain builds from source on the VPS.** This was the original (2026-09-09)
design and it is wrong - it was corrected on 2026-09-12 after discovering that ShopDeck,
Identity, Inventory, and Packing had all already migrated away from that exact pattern to a
GHCR-images-only model, and Brain's deploy scripts had simply never been updated to match.

The real, current model, identical to every other AaramBooks service:

1. Code lives in the `aarambooks` GitHub repo (`sums0907/aarambooks`) - this is Brain's own
   repo; unlike ShopDeck/Identity/Inventory/Packing, Brain was never extracted out of the
   original monorepo, so this repo name does not have "brain" in it.
2. `.github/workflows/docker-publish.yml` builds `Dockerfile.prod` and pushes the result to
   `ghcr.io/sums0907/aarambooks-brain-core:main` on every push to `main` (also
   `workflow_dispatch`-able manually). This is a GitHub Container Registry (GHCR) image - a
   packaged, ready-to-run copy of the app - not a second GitHub repository. It will not show
   up in `sums0907`'s repo list; it shows up under GitHub's Packages UI once published.
3. The VPS never checks out this repo's source at all. `~/aarambooks/brain/` on the VPS
   contains exactly three files - `docker-compose.prod.yml`, `.env`,
   `litellm_config.prod.yaml` - and nothing else. No `.git` directory should ever exist
   there; if one appears, that is a mistake to be cleaned up, not a feature (see
   `docs/claude/VPS_CLEANUP_PLAN_BRAIN_MONOREPO_CLONE.md` for the incident that established
   this).
4. Deploying = pull the new image, restart the container, run migrations. Never `git pull`,
   never `docker compose build` on the VPS.

## 3. One-time infrastructure setup (already done - here for rebuilding on a new VPS)

Skip this section for a routine deploy to the existing VPS; go to Section 5. This section is
for standing Brain up on a *new* VPS from nothing.

### 3a. DNS
Two records exist in Cloudflare, both proxied, both pointing at the VPS's IP
(`200.234.39.72` as of 2026-09-12 - confirm this hasn't changed):
- `api-brain.aarambooks.cloud` - **the one actually in use.** This is what nginx proxies, what
  Exotel's and Sarvam's webhooks call back into, and what `/health` is checked against.
- `brain.aarambooks.cloud` - created alongside it on 2026-09-12, but **not yet wired to
  anything** - no nginx site config exists for it. Its intended purpose was never specified.
  Do not assume it does anything until an nginx config is deliberately created for it.

### 3b. nginx + TLS (requires sudo on the VPS - cannot be done by an AI agent without a human
present to supply the password interactively)
```
sudo tee /etc/nginx/sites-available/api-brain.aarambooks.cloud > /dev/null <<'EOF'
server {
    listen 80;
    server_name api-brain.aarambooks.cloud;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/api-brain.aarambooks.cloud /etc/nginx/sites-enabled/api-brain.aarambooks.cloud
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api-brain.aarambooks.cloud --non-interactive --agree-tos -m <real email>
```
This mirrors the exact live config of `api-shopdeck.aarambooks.cloud`, read directly from the
VPS before writing this, not guessed. Certbot rewrites the file in place to add the HTTPS
server block and the HTTP→HTTPS redirect, and registers its own auto-renewal - nothing further
is needed for renewal.

### 3c. VPS directory
```
mkdir -p ~/aarambooks/brain
```
Matches the sibling convention already used for every other service
(`~/aarambooks/identity`, `~/aarambooks/inventory`, `~/aarambooks/packing`,
`~/aarambooks/business_systems/shopdeck`).

### 3d. GHCR auth on the VPS
Already present (confirmed via `~/.docker/config.json` containing a `ghcr.io` entry) because
every other service's private images already pull successfully. If standing up a genuinely
new VPS, this needs `docker login ghcr.io` once with a PAT that has `read:packages` scope.

## 4. Every environment variable - what it does, where it's read, what happens if it's wrong

Brain has **three separate places that read configuration**, not one - this is a real,
easy-to-miss gotcha:

1. **`src/shared/config.py`'s `Settings` class** - the main one. Reads every field below
   (case-insensitive match: env var `DATABASE_URL` → field `database_url`) from `.env` or the
   real process environment. `extra="ignore"` means an unrecognized env var is silently
   ignored, not an error - a typo'd variable name fails silently, not loudly.
2. **`src/intelligence_domains/ndr/config.py`'s `NDRSettings` class** - separate class,
   separate env prefix (`NDR_`). Only two fields exist here:
   `NDR_MAX_CONCURRENT_CALLS` (int, default `1`) and `NDR_RESCHEDULE_WINDOW_DAYS` (JSON dict
   string, default `{"1": 2, "2": 2, "3": 0}`). Neither is currently set in production - both
   are running on their defaults.
3. **Two raw `os.environ.get()` reads that bypass both Settings classes entirely**:
   - `AZM_DATABASE_URL` (`src/azm/config.py`) - **not** read from `settings.database_url`, a
     completely separate variable. Defaults to a dev-only SQLite-adjacent Postgres URL if
     unset. Must be set explicitly for AZM's persistent storage to work in production (see
     Section 6).
   - `LITELLM_MASTER_KEY` (`src/infrastructure/adapters/litellm_gateway.py`) - read directly
     via `os.environ.get("LITELLM_MASTER_KEY", settings.litellm_api_key)`. Note the fallback
     is `settings.litellm_api_key`, populated from a *different* env var (`LITELLM_API_KEY`,
     not set in production) - so in practice, whatever `LITELLM_MASTER_KEY` is set to is what
     both Brain's own gateway client AND the `litellm` container itself will use (the compose
     file passes the same `.env` value to both), since they're referencing the identical
     variable. Never set `LITELLM_API_KEY` and `LITELLM_MASTER_KEY` to different values -
     only `LITELLM_MASTER_KEY` matters in the current wiring.

### 4a. Fields whose `.env` value is irrelevant - overridden by `docker-compose.prod.yml`

These exist in `.env` for documentation/local-dev-parity only. Whatever `docker-compose.prod.yml`'s
own `environment:` block sets for `aarambooks-brain-api` wins, regardless of `.env`:

| Variable | Compose overrides to | Why |
|---|---|---|
| `PORT` | `8000` | fixed |
| `ENVIRONMENT` | `production` | fixed |
| `DATABASE_URL` | `postgresql+asyncpg://${DB_USER:-postgres}:${DB_PASSWORD}@aarambooks-brain-db:5432/${DB_NAME:-aarambooks_brain_core_prod}` | must point at the sibling container by service name, not localhost |
| `MONGO_URI` | `mongodb://aarambooks-brain-mongo:27017` | same reason |
| `LITELLM_BASE_URL` | `http://litellm:4000` | same reason |

`DATABASE_URL_SYNC` is not read by any Settings class at all (grep confirms - only
`scripts/setup_db.py`, itself now superseded by Alembic, ever read it via raw
`os.environ.get`). Safe to leave as an inert placeholder or omit entirely.

### 4b. Fields that must be correct in the real `.env` (compose does not override these)

**AI infrastructure:**
| Variable | Purpose | Real value source |
|---|---|---|
| `LITELLM_MASTER_KEY` | Auth key for the LiteLLM gateway - shared by Brain's own client and the litellm container | Generate fresh per environment (`openssl rand -hex 24`, prefix `sk-`) - **do not reuse dev's `sk-1234`**, it's a guessable placeholder |
| `LITELLM_MODEL` | Which stage-routing name `LiteLLMGatewayAdapter` defaults to when none is passed | `local-qwen` (name only - see below for what it resolves to) |
| `GEMINI_API_KEY` | Real Gemini API key | From Google AI Studio / GCP console |
| `LLM_ENFORCE_JSON_FORMAT` | `true`/`false` | Behavioral flag, not environment-specific |
| `LLM_ROUTING_MAX_TOKENS` | int | Behavioral flag, not environment-specific |
| `STAGE_R_1_INTENT_ROUTING_MODEL`, `STAGE_R_2_PLANNING_MODEL`, `STAGE_R_5_ENTITY_RESOLUTION_MODEL`, `STAGE_R_7_RESPONSE_SYNTHESIS_MODEL`, `STAGE_5_ANALYTICS_ENGINE_MODEL` | All `local-qwen` | **Decided 2026-09-12: production routes `local-qwen` to Gemini, not Ollama** (see Section 7, `litellm_config.prod.yaml`) - do not change these names, the routing target is controlled entirely by the litellm config file, not by changing these to say "gemini" directly |
| `STAGE_6_EXECUTIVE_REPORTS_MODEL` | `gemini-3.6-flash` | Already Gemini-routed in both dev and prod |

**External ecosystem URLs:**
| Variable | Production value | Status |
|---|---|---|
| `IDENTITY_URL` | `https://api-identity.aarambooks.cloud` | live, confirmed working (real token exchange succeeded during the 2026-09-12 deploy) |
| `INVENTORY_URL` | `https://api-inventory.aarambooks.cloud` | live |
| `SHOPDECK_URL` | `https://api-shopdeck.aarambooks.cloud` | live, confirmed working (real NDR queue claim call succeeded) |
| `PACKING_URL` | `https://api-packing.aarambooks.cloud` | live - **do not use dev's `http://localhost:8001`, it does not exist on the VPS** |
| `CATALOG_URL` | defaults to `http://localhost:8300` if unset | **Catalog is not deployed to any VPS as of 2026-09-12.** Leaving this unset/at default is a known, accepted gap - only breaks the catalog-artifact-download route, not core NDR calling. Do not invent a URL for a service that doesn't exist yet. |
| `CATALOG_INTERNAL_TOKEN`, `SHIPROCKET_TOKEN`, `SHOPDECK_TOKEN` | not currently set | present in `.env.example` as placeholders; not confirmed needed by any currently-active code path - leave unset unless a specific feature requires them |

**Identity M2M credentials:**
| Variable | Notes |
|---|---|
| `BRAIN_CLIENT_ID`, `BRAIN_CLIENT_SECRET` | Confirmed by the user on 2026-09-12 to be real production Identity credentials (not staging). Verified working directly - the real deploy's startup logs showed a successful `POST https://api-identity.aarambooks.cloud/auth/service-token → 200 OK`. If these ever need rotating, get new ones from Identity's own admin/M2M client registration - never invent a client ID here. |

**Exotel (voice provider #1):**
| Variable | Notes |
|---|---|
| `EXOTEL_ACCOUNT_SID`, `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_CALLER_ID` | Real Exotel account credentials, from the Exotel dashboard |
| `EXOTEL_VOICEBOT_FLOW_URL` | The specific voicebot flow's URL from the Exotel console |
| `AARAM_EXOTEL_WEBHOOK_SECRET` | Shared secret Brain checks incoming Exotel webhooks against - generate fresh, must match whatever Exotel is configured to send |
| `EXOTEL_WEBHOOK_BASE_URL` | **Must be `https://api-brain.aarambooks.cloud` in production.** Dev uses an ngrok tunnel URL - copying that into production means Exotel tries to call back to a developer's laptop instead of the live server. |
| `EXOTEL_VOICEBOT_FLOW_URL_STAGING` | Optional - a separate staging-only bot flow, if one has been created in the Exotel console. Empty is fine. |

**Sarvam (voice provider #2):**
| Variable | Notes |
|---|---|
| `SARVAM_API_KEY` | A Voice-Agents-specific key - **not** interchangeable with a standard Sarvam TTS/STT API key, per Sarvam's own docs |
| `SARVAM_AGENT_ID`, `SARVAM_WORKSPACE_ID`, `SARVAM_ORG_ID`, `SARVAM_CONNECTION_ID` | From the Sarvam dashboard for the specific configured voice agent |
| `SARVAM_WEBHOOK_SECRET` | Checked by `verify_sarvam_bearer()` against the `?secret=` query param Sarvam is configured to send (Sarvam's `webhook_config` has no header-auth field at all, so this is the only mechanism) |
| `SARVAM_WEBHOOK_BASE_URL` | **Must be `https://api-brain.aarambooks.cloud` in production**, same reasoning as Exotel's |
| `SARVAM_APP_VERSION` | **Not settled as of 2026-09-12** (confirmed directly with the user). Code defaults to `4`, explicitly marked in `src/shared/config.py` as an unconfirmed draft. Do not assume this default is correct - confirm with the user before placing a real Sarvam Instant Outbound call in production. |
| `TEST_PHONE_OVERRIDE` | **Must be unset/absent in production.** If set, every single outbound call (both Exotel and Sarvam, confirmed via direct code read of both adapters plus `ccc_builder.py`) is silently redirected to this one fixed number instead of the real customer. This is dev's own safety mechanism for testing without dialing real numbers - it is not a feature to carry into production under any circumstances. |

### 4c. Fields that only exist for `docker-compose.prod.yml` itself, not for Brain's own Settings

| Variable | Used by | Notes |
|---|---|---|
| `DB_PASSWORD` | `aarambooks-brain-db` and the `DATABASE_URL` compose builds for `aarambooks-brain-api` | **Required - compose fails to start with no default (`${DB_PASSWORD:?DB_PASSWORD required}`)**. Generate fresh per environment - dev's Postgres has no real password (`postgres`/`postgres`), never reuse that. **If ever regenerating this on a live deployment, you must also run `ALTER USER postgres WITH PASSWORD '...'` against the actual running Postgres container AND update `AZM_DATABASE_URL` to match (Section 4d) AND restart `aarambooks-brain-api` - all three, or the app will start failing every database call.** |
| `DB_USER` | same | Optional, defaults to `postgres` |
| `DB_NAME` | same | Optional, defaults to `aarambooks_brain_core_prod` |

### 4d. `AZM_DATABASE_URL` - added 2026-09-12, easy to forget entirely

Not read by either Settings class - a raw `os.environ.get()` in `src/azm/config.py`. Must be
set explicitly to the same Postgres instance the rest of the app uses, from inside the Docker
network:
```
AZM_DATABASE_URL=postgresql://postgres:<the real DB_PASSWORD value>@aarambooks-brain-db:5432/aarambooks_brain_core_prod
```
**If this is missing entirely**, AZM does not crash - it logs
`WARNING:src.azm.provider:AZM persistent provider unavailable (...). Falling back to
bootstrap.` and runs in a non-persistent fallback mode. This is easy to miss because nothing
fails loudly. Check for the absence of this warning in `docker logs aarambooks-brain-api` as
part of every deploy's verification (Section 8).

**Security note**: never `print()` or log this URL in full - it contains the real password.
`src/azm/azm_init.py` (Section 6) had exactly this bug once (fixed 2026-09-12, redacts to
`postgresql://postgres:***@...` now) - if writing any new tooling that touches this URL,
redact it the same way.

### 4e. Full checklist - copy this when building a real `.env` from scratch

```
PORT=8000
ENVIRONMENT=production
DATABASE_URL=unused-overridden-by-docker-compose.prod.yml
DATABASE_URL_SYNC=unused-overridden-by-docker-compose.prod.yml
DB_PASSWORD=<generate fresh>
LITELLM_MASTER_KEY=<generate fresh>
LITELLM_BASE_URL=http://localhost:4000
LITELLM_MODEL=local-qwen
GEMINI_API_KEY=<real key>
LLM_ENFORCE_JSON_FORMAT=false
LLM_ROUTING_MAX_TOKENS=250
STAGE_R_1_INTENT_ROUTING_MODEL=local-qwen
STAGE_R_2_PLANNING_MODEL=local-qwen
STAGE_R_5_ENTITY_RESOLUTION_MODEL=local-qwen
STAGE_R_7_RESPONSE_SYNTHESIS_MODEL=local-qwen
STAGE_5_ANALYTICS_ENGINE_MODEL=local-qwen
STAGE_6_EXECUTIVE_REPORTS_MODEL=gemini-3.6-flash
IDENTITY_URL=https://api-identity.aarambooks.cloud
INVENTORY_URL=https://api-inventory.aarambooks.cloud
PACKING_URL=https://api-packing.aarambooks.cloud
SHOPDECK_URL=https://api-shopdeck.aarambooks.cloud
BRAIN_CLIENT_ID=<real Identity M2M client id>
BRAIN_CLIENT_SECRET=<real Identity M2M secret>
AARAM_EXOTEL_WEBHOOK_SECRET=<real>
EXOTEL_ACCOUNT_SID=<real>
EXOTEL_API_KEY=<real>
EXOTEL_API_TOKEN=<real>
EXOTEL_CALLER_ID=<real>
EXOTEL_VOICEBOT_FLOW_URL=<real>
EXOTEL_WEBHOOK_BASE_URL=https://api-brain.aarambooks.cloud
SARVAM_API_KEY=<real>
SARVAM_AGENT_ID=<real>
SARVAM_WORKSPACE_ID=<real>
SARVAM_ORG_ID=<real>
SARVAM_CONNECTION_ID=<real>
SARVAM_WEBHOOK_BASE_URL=https://api-brain.aarambooks.cloud
SARVAM_WEBHOOK_SECRET=<real>
# SARVAM_APP_VERSION intentionally omitted - not settled, confirm with the user first
AZM_DATABASE_URL=postgresql://postgres:<same value as DB_PASSWORD>@aarambooks-brain-db:5432/aarambooks_brain_core_prod
# TEST_PHONE_OVERRIDE intentionally omitted - must never be set in production
```

## 5. Every database and what manages its schema

| Store | Container | Schema managed by | Tables |
|---|---|---|---|
| PostgreSQL (pgvector) | `aarambooks-brain-db` (`pgvector/pgvector:pg16`) | **Alembic** (`alembic/`, `alembic.ini`, baked into the image) | `core_memories`, `core_suspended_actions` (both from `postgres_memory.py`), `core_knowledge` (`postgres_knowledge.py`, has a `Vector(768)` embedding column), `sabaq_evidence` (`postgres_sabaq.py`), plus `alembic_version` |
| PostgreSQL (same instance) | same | **`src/azm/azm_init.py`** - raw SQL, not Alembic, not SQLAlchemy at all | 10 `azm_*` tables (`azm_namespaces`, `azm_concepts`, `azm_aliases`, `azm_relationships`, `azm_attr_mappings`, `azm_external_mappings`, `azm_ingestion_runs`, `azm_provenance`, `azm_schematic_attrs`, `azm_schematic_refs`) |
| MongoDB | `aarambooks-brain-mongo` (`mongo:7`) | No migration tool - `engagement_repo.setup_indexes()` runs on every app startup (`src/main.py`'s lifespan), idempotently creating whatever indexes are needed. No manual step required. |

**There is no more `scripts/setup_db.py` fallback path for Postgres** as of 2026-09-12 - it
was superseded by real Alembic because it was itself broken (only ever registered one of the
four SQLAlchemy models, would have silently created just `sabaq_evidence` and nothing else).
Do not resurrect it. Any future SQLAlchemy model change needs a real
`alembic revision --autogenerate -m "..."`, generated against a genuinely empty database (not
the shared dev database, which already has drift), reviewed for the two known false-negative
gaps autogenerate has (see Section 6) before trusting it.

The `pgvector` Postgres extension (`CREATE EXTENSION IF NOT EXISTS vector`) is created by the
Alembic baseline migration itself (`alembic/versions/822cb633d5c8_...py`) - not a separate
manual step.

## 6. Known gotchas found the hard way - do not rediscover these

1. **Alembic autogenerate does not add the `pgvector` import or the `CREATE EXTENSION`
   statement automatically.** If a future model adds a new `Vector(...)` column, check the
   generated migration file has `import pgvector.sqlalchemy` at the top and that
   `CREATE EXTENSION IF NOT EXISTS vector` exists before any `Vector` column is created - it
   will not add either on its own, and running an unreviewed autogenerated migration with a
   `Vector` column against a genuinely fresh database will fail.
2. **`.env` files do not support `${VAR}` interpolation.** A line like
   `DATABASE_URL=postgresql://user:${DB_PASSWORD}@host/db` inside `.env` is passed through
   *literally*, including the unexpanded `${DB_PASSWORD}` text - it does not get substituted.
   (`docker-compose.prod.yml`'s own top-level `${VAR}` syntax works differently - that's
   Compose's own variable substitution for the compose file itself, not for `.env` file
   contents passed through `env_file:`.)
3. **`src/azm/azm_init.py` needs to run once per fresh database, and is idempotent** -
   `python -m src.azm.azm_init` inside the running `aarambooks-brain-api` container. As of
   2026-09-12 this is automated into `mac_to_vps_deploy.sh` (runs on every deploy, `|| true`
   so a failure doesn't block the rest of the script) - it does not need to be run manually
   anymore, but if running any other deploy path (e.g. a manual SSH session), remember this
   step exists.
4. **AZM's own schema-verification query used to be hardcoded to SQLite's `sqlite_master`
   table unconditionally** - fixed 2026-09-12 to branch on `conn.is_sqlite` and use
   `information_schema.tables` for PostgreSQL. If touching `src/azm/azm_init.py` or
   `src/azm/db.py` again, preserve this branching - it's easy to accidentally special-case
   only one backend again.
5. **Never let any tool print `AZM_DATABASE_URL`, `DATABASE_URL`, or any other connection
   string in full** - they contain real passwords. `azm_init.py`'s own log line leaked the
   real production `DB_PASSWORD` into a Claude Code session transcript once (2026-09-12); it
   now redacts via a small `_redact()` helper. Follow that pattern in any new tooling.
6. **The deploy mechanism is GHCR-images-only, not git-pull-and-build** (Section 2) - this
   was gotten wrong once already (2026-09-09's original design) and cost a full rebuild of
   the deploy scripts on 2026-09-12. If anything you're about to write assumes `git pull` on
   the VPS, stop and re-read Section 2.
7. **`ci.yml` and `docker-publish.yml` both build `Dockerfile.prod` independently on every
   push** - redundant (doubles CI time) but harmless; `ci.yml`'s build is purely a validation
   gate and pushes nothing anywhere. Not worth "fixing" unless CI time becomes a real problem.
8. **`~/aarambooks/brain/.env` on the VPS is not gitignored by virtue of being on the VPS** -
   it's simply never been committed anywhere, it only exists as a file on disk there. Locally,
   `.gitignore` has `.env` and `.env.*` (the latter added 2026-09-12 specifically to stop a
   future `.env.production`-style file from being swept into a commit by `mac_to_vps_deploy.sh`'s
   `git add .`). Never create a secrets-bearing file in the repo root without confirming it
   matches a gitignore pattern first.

## 7. Config files that must exist on the VPS - not from git, placed once and updated in place

All three live in `~/aarambooks/brain/` and are never checked out from git - they were placed
via `scp` from a developer machine and are edited in place on the VPS from then on (or
re-scp'd when their local source changes):

- **`docker-compose.prod.yml`** - defines all 4 services. If this file's local copy
  (`/Users/sumatidhingra/aarambooks/docker-compose.prod.yml`) changes, it must be re-copied to
  the VPS (`scp docker-compose.prod.yml aaramhomes@200.234.39.72:~/aarambooks/brain/`) - a
  normal `git push` + redeploy does **not** update this file on the VPS, since the VPS never
  pulls from git at all.
- **`.env`** - built once per Section 4, never generated automatically, never checked into
  git. Edited in place on the VPS for any credential rotation or config change.
- **`litellm_config.prod.yaml`** - routes `local-qwen` (the stage-routing name Brain's code
  uses) to `gemini/gemini-2.0-flash` via the `litellm` container. **Decided 2026-09-12:
  Gemini, not Ollama** - the user explicitly ruled out running Ollama/Qwen on the VPS
  ("can't bloat up my VPS with heavy Qwen"). This is the exact same real Gemini model already
  proven working for the analytics stages in dev - not a new integration. Like
  `docker-compose.prod.yml`, changes to the local copy require a re-`scp`, not a git-based
  redeploy.

## 8. Step-by-step: routine deploy (code already exists, VPS already bootstrapped)

This is what `mac_to_vps_deploy.sh` automates end-to-end. Run it from a developer machine (or
any machine with `git`, `gh`, and `ssh` access configured) with the repo checked out:

```
./mac_to_vps_deploy.sh "commit message describing the change"
```

What it does, in order (matches Aaram_Inventory's proven script structure exactly):
1. `git add . && git commit && git push origin main`.
2. Watches the triggered `docker-publish.yml` GitHub Action via `gh run watch` - **stops and
   does not touch the VPS at all if this fails.**
3. SSHes to the VPS, `cd ~/aarambooks/brain`, `docker compose -f docker-compose.prod.yml pull`,
   `docker compose -f docker-compose.prod.yml up -d` (recreates only the containers whose
   image actually changed).
4. `docker exec aarambooks-brain-api alembic upgrade head || true` - runs any pending Postgres
   migrations.
5. `docker exec aarambooks-brain-api python -m src.azm.azm_init || true` - idempotent, safe to
   run every time.
6. `docker image prune -f` to reclaim disk space from now-unused old image layers.
7. Prints each container's actual restart time as final proof something really happened, not
   just that the script exited 0.

**If `docker-compose.prod.yml` or `litellm_config.prod.yaml` changed locally**, re-`scp` them
to the VPS *before* running the deploy script (Section 7) - the script itself never copies
these files, only pulls the application image.

**If new environment variables were added** (a new required setting, a new secret), edit
`~/aarambooks/brain/.env` directly on the VPS *before* redeploying, since nothing
automatically syncs `.env` from anywhere.

## 9. Step-by-step: verifying a deploy actually worked - do not stop at "the script exited 0"

In order, each one gating trust in the next:

1. `docker compose -f docker-compose.prod.yml ps` on the VPS - all 4 containers `Up`,
   `aarambooks-brain-api` specifically reporting `(healthy)`, not just `Up`.
2. `docker logs aarambooks-brain-api --tail 60` - look for, in order:
   - `Application startup complete.`
   - `Started NDR Queue Poller` and `Started Outbound Writeback Worker` - both background
     workers actually started, not just imported.
   - A real `POST https://api-identity.aarambooks.cloud/auth/service-token` returning
     `200 OK` - proves `BRAIN_CLIENT_ID`/`SECRET` are valid, not just present.
   - **Absence** of `WARNING:src.azm.provider:AZM persistent provider unavailable` - its
     presence means `AZM_DATABASE_URL` or `psycopg2-binary` is missing or wrong.
   - No `Traceback` or `ERROR` lines.
3. `curl https://api-brain.aarambooks.cloud/health` from *outside* the VPS (your own machine,
   not an SSH session) - real `{"status":"ok","service":"aarambooks-brain-api","environment":"production"}`.
   This is the only step that proves DNS, Cloudflare, nginx, and TLS all work together, not
   just that the container itself is fine.
4. `docker exec aarambooks-brain-db psql -U postgres -d aarambooks_brain_core_prod -c "\dt"` -
   confirm all 4 Alembic-managed tables plus `alembic_version` exist.
5. **Not yet proven as of 2026-09-12, still needed before real customer traffic**: a real
   Exotel webhook round-trip, a real Sarvam webhook round-trip, and one real NDR queue item
   flowing all the way through to a dispatched call and a confirmed ShopDeck writeback. The
   steps above prove Brain is running correctly; they do not prove a live call works
   end-to-end.

## 10. Rollback

Since the VPS never builds from source, rolling back code means pointing the VPS at an older
already-published image tag rather than reverting a git commit and rebuilding:
```
# find the previous good image digest from GitHub's package history, then on the VPS:
docker pull ghcr.io/sums0907/aarambooks-brain-core@sha256:<previous digest>
docker tag ghcr.io/sums0907/aarambooks-brain-core@sha256:<previous digest> ghcr.io/sums0907/aarambooks-brain-core:main
docker compose -f docker-compose.prod.yml up -d
```
**A code rollback alone does not undo a database migration that already ran.** If the bad
deploy included an Alembic migration, also run
`docker exec aarambooks-brain-api alembic downgrade -1` (or to a specific revision) - check
`alembic history` inside the container first to know what "-1" actually targets. AZM's schema
is additive/idempotent only (`CREATE TABLE IF NOT EXISTS`) - it has no downgrade path, and
none has ever been needed.

## 11. Explicitly out of scope for this runbook - known, tracked, not yet done

- Catalog Business System has no VPS deployment at all yet - `CATALOG_URL` has no real target
  to point at.
- `SARVAM_APP_VERSION` is still an unconfirmed draft (`4`) - confirm with the user before any
  real Sarvam Instant Outbound call is placed from this deployment.
- `ShopDeckMasterCCCBuilder`'s constructor accepts an unused `inventory_provider` argument -
  harmless, not fixed.
- Three scripts (`dry_run_bnctest1.py`, `scripts/business_value_e2e_test.py`,
  `scripts/run_phase5b_benchmark.py`) still call `CatalogCemAdapter` with an old, removed
  constructor signature - would crash if run, but none of them run automatically.
- `TEST_PHONE_OVERRIDE` has no environment-level enforcement (Section 4b already covers the
  operational rule: never set it in production) - a proposal to make this impossible to set
  by accident (rather than just documented as forbidden) was never authorized.
