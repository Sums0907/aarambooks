# Brain VPS deployment strategy

Written by: Claude
Context: Brain has never been deployed to the VPS. Identity, Inventory, and ShopDeck BS
already are, each via its own `mac_to_vps_deploy.sh` (Inventory's and ShopDeck's were read
directly to derive this), plus `AaramLauncher/start_all.sh` for local dev. This document
adapts that same proven pattern to Brain and calls out where Brain's actual current code
would break it if deployed as-is today.

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

Brain's deployment should follow this exact shape. Because Brain lives at the monorepo root
(not a subfolder like `business_systems/shopdeck`), its version of the script skips the
subfolder `cd` that ShopDeck's needs.

## What I found broken or missing, and fixed

Constructing this strategy meant actually trying to build the artifact the VPS would build,
not just writing a script that assumes it works. Four real gaps turned up:

1. **The existing root `Dockerfile` is a non-functional placeholder.** It copies only `src/`
   and its `CMD` is `python -c "import time; ...; time.sleep(86400)"` - it never runs
   uvicorn, so containerizing Brain with it would produce a container that does nothing.
   Its own comment ("if physical transport is later authorized") marks it as a relic from
   before Brain was allowed to place real calls. Left untouched (it may still be intentional
   for some dev/CI use), and added `Dockerfile.prod` alongside it - matching how ShopDeck has
   both an implicit dev setup and a distinct `Dockerfile.prod` - that actually runs
   `uvicorn src.main:app` and also copies `business_systems/catalog/` (needed by
   `src/main.py`'s catalog-artifact download route; `business_systems/shopdeck` is
   deliberately excluded since it's ShopDeck's own separately deployed service).

2. **`python-dotenv` was missing from `requirements.txt`.** `src/main.py` line 4 does
   `from dotenv import load_dotenv` unconditionally. It happens to be installed in the local
   `.venv` (probably a stray `pip install` from early on), but a fresh container build from
   `requirements.txt` alone would crash on the very first import with
   `ModuleNotFoundError: No module named 'dotenv'`. **Fixed**: added
   `python-dotenv==1.2.3` to `requirements.txt`.

3. **`MONGO_URI` was not a real, settable config field.** `src/main.py`'s lifespan did
   `mongo_uri = getattr(settings, "mongo_uri", "mongodb://localhost:27017")` - but
   `Settings` never declared a `mongo_uri` field, so pydantic-settings had nothing to
   populate from the environment and that `getattr` always silently fell through to the
   hardcoded localhost default, regardless of what `MONGO_URI` was set to. On a VPS where
   Mongo runs in its own container (not on Brain's container's own `localhost`), this would
   have failed to connect. **Fixed**: added a real `mongo_uri: str = "mongodb://localhost:27017"`
   field to `Settings` (`src/shared/config.py`) and simplified `main.py` to read it directly.
   Verified: `MONGO_URI=mongodb://mongo:27017` now actually reaches `settings.mongo_uri`.

4. **CI built the wrong Dockerfile.** `.github/workflows/ci.yml`'s "Build Production Image"
   step ran `docker build -t aarambooks-brain-core:prod .` - which builds the placeholder
   `Dockerfile`, not the real prod artifact. **Fixed**: pointed it at
   `docker build -f Dockerfile.prod ...` so CI actually gates on what the VPS will run.

## The one gap I found but did NOT fix - needs your decision, not mine

**`litellm_config.yaml` routes every conversational stage through a local Ollama instance.**
`stage_r_1/2/5/7` (intent routing, planning, entity resolution, response synthesis - i.e.
the models actually generating Priya's side of a live NDR call) all resolve to
`local-qwen`, which `litellm_config.yaml` points at
`ollama/qwen2.5-coder:7b @ http://host.docker.internal:11434` - Docker's alias for the
**developer's own Mac**. Only the two non-conversational analytics/reporting stages already
use a real cloud model (Gemini).

On a VPS, `host.docker.internal` resolves to nothing unless Ollama is separately installed
and running there. This is not a small oversight to patch quietly - it's a real product
decision with cost and quality implications for a system that will be talking to real
customers:

- **Option A**: install and run Ollama on the VPS itself, sized to serve `qwen2.5-coder:7b`
  at conversational (sub-few-second) latency for live phone calls - real capacity planning
  needed, and a new single point of failure for every call.
- **Option B**: point production's conversational stages at Gemini instead (already
  integrated, already used for the analytics stages).

I drafted `litellm_config.prod.yaml` implementing Option B as a safe, working default (same
stage-routing *names* your code already expects, so no code change needed - just the
`model_name: "local-qwen"` target changes from Ollama to Gemini) - but I did not silently
wire it in as the only path, and did not decide this for you. Review it, and either approve
it or tell me to build out Option A instead before this goes anywhere near a real customer.

## Artifacts created (not yet committed)

- `Dockerfile.prod` - real production image, runs uvicorn, copies only what Brain needs
- `docker-compose.prod.yml` - self-contained stack: brain-api, its own pgvector Postgres,
  its own MongoDB (new - Brain has never had a containerized Mongo before), its own litellm
  gateway. No dependency on the developer's Mac for anything, unlike the dev compose file.
- `litellm_config.prod.yaml` - see the Ollama/Gemini decision above
- `mac_to_vps_deploy.sh` - same three-step pattern as Inventory/ShopDeck's, adapted for
  Brain living at the repo root (no subfolder `cd`)
- `.env.example` - documented the newly-real `MONGO_URI` variable

## What is still open - infrastructure outside any repo I can inspect

`api-identity.aarambooks.cloud`, `api-inventory.aarambooks.cloud`, and
`api-shopdeck.aarambooks.cloud` are all live HTTPS domains today, but nothing in any of the
three repos I read (this one, Aaram_Inventory, or the launcher) shows how they're
terminated - no nginx config, no Caddyfile, no Traefik labels anywhere. That reverse-proxy
and TLS layer is managed directly on the VPS, outside version control I have access to.
Brain will need the same treatment for whatever domain it's given (e.g.
`api-brain.aarambooks.cloud`) - a manual, one-time step on the VPS itself, since I can't see
or safely guess at that configuration. This also gates Exotel's webhook: Exotel needs a real
public HTTPS URL to call back into Brain's `/api/customer-engagement/voice/exotel/*` routes,
and `EXOTEL_WEBHOOK_BASE_URL` needs to be set to it.

## Recommended phased rollout

1. **Land the code fixes** (`requirements.txt`, `config.py`/`main.py`, `ci.yml`) - safe,
   already verified, no infra dependency. Push and confirm CI goes green on the new
   `Dockerfile.prod` build.
2. **Decide the LLM routing question above.** Everything downstream assumes this is settled.
3. **Provision the VPS-side reverse proxy/TLS/domain** for Brain - whoever manages that box's
   existing nginx/Caddy/Traefik setup for the other three services adds Brain the same way.
4. **Fill in the real `.env` on the VPS** - production DB password, Mongo URI (matches the
   compose file's internal service name automatically if using the file as-is),
   `LITELLM_MASTER_KEY`, `GEMINI_API_KEY`, real `BRAIN_CLIENT_ID`/`SECRET` (Identity M2M
   creds, not the staging ones from `.env.example`), real Exotel account credentials, and
   `EXOTEL_WEBHOOK_BASE_URL` pointing at the domain from step 3.
5. **First deploy**: run `./mac_to_vps_deploy.sh "Initial Brain production deployment"`.
   Confirm all four containers report healthy (`docker compose -f docker-compose.prod.yml ps`
   on the VPS).
6. **Smoke test before any real customer touches it** - in this order, each gating the next:
   - `curl https://<brain-domain>/health` returns `{"status": "ok", ...}`
   - A real webhook round-trip: point one real Exotel test call at the new URL and confirm
     `session-start` → `transcript` → `session-end` all land correctly in Mongo
     (this repo already has `scripts/inspect_real_context.py` for a read-only version of the
     upstream half of this - claims one real queue item and prints what would be sent to
     Exotel, without dispatching)
   - Confirm `NDR_MAX_CONCURRENT_CALLS` and the outbound writeback worker are both actually
     running in the deployed process (check the startup logs for both "Started NDR Queue
     Poller" and "Started Outbound Writeback Worker" - both blockers this session already
     found and fixed for the *code*, but neither has been proven running in this specific
     deployed environment yet)
   - Only after all of the above: let one real NDR queue item flow all the way through to a
     real dispatched call, and manually verify ShopDeck reflects the outcome afterward.
7. **Roll back plan**: since the VPS builds directly from `git pull`, rolling back is
   `git checkout <last-good-sha> -- .` on the VPS followed by the same `up -d --build` - no
   registry/image-tag bookkeeping needed, but confirm this before you need it under pressure,
   not during an incident.
