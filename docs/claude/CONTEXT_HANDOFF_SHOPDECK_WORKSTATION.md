# Context handoff — ShopDeck: new repo, new pipeline, VPS cutover done

Written by: Claude
Date: 2026-09-09
Why this exists: ShopDeck was just split into its own fully independent repo and moved to
an images-only VPS deployment model, and the live production containers were cut over to
it. Read this before touching ShopDeck's deploy script, docker-compose.prod.yml, or the
VPS directly.

## TL;DR

- ShopDeck's only repo now is **`github.com/Sums0907/aarambooks-shopdeck`**. Nothing else.
- The VPS pulls **pre-built Docker images from GHCR** — no git, no source code, no `--build`
  on the VPS at all anymore.
- The live production containers were **already cut over** to this new model (see below) -
  they're running the new images right now, verified working.
- **You have uncommitted work sitting in this repo right now** (`backend/api/main.py`,
  `orders.py`, `sync_shopdeck_mcp_data.py`, `frontend/src/App.jsx`, a new
  `backend/api/routers/insights.py` + `frontend/src/screens/Insights.jsx`, etc.) - see the
  "your in-flight work" section, this matters for how you deploy next.

## What changed and why

ShopDeck and Catalog used to share one combined repo, `aarambooks-business-systems`. Per
explicit instruction they were split into two fully disjoint repos - separate git history,
separate CI, separate production databases, zero sharing:

- `github.com/Sums0907/aarambooks-shopdeck` (this one)
- `github.com/Sums0907/aarambooks-catalog`

The old combined repo is now **archived** (permanently read-only on GitHub) - if any
terminal or IDE window still has a clone pointing at it as `origin`, pushes from there will
now fail outright rather than silently drifting into a second history. If you hit that,
switch that clone's remote to `aarambooks-shopdeck`.

Separately, and more consequentially: **the VPS deployment model changed from
build-from-source to images-only**, matching how Identity/Inventory/Packing already work.
The old `docker-compose.prod.yml` had `build: context: . dockerfile: Dockerfile.prod` and
bind-mounted `.:/app` into `shopdeck-api`/`shopdeck-sync` - meaning the containers were
actually serving whatever code sat on the VPS's local disk at
`~/aarambooks/business_systems/shopdeck`, not anything baked into an image. That's gone now.

## The new pipeline

`.github/workflows/docker-publish.yml` builds and pushes two images on every push to `main`:
- `ghcr.io/sums0907/aarambooks-shopdeck-backend:main` (serves both `shopdeck-api` and
  `shopdeck-sync` - same image, different `command:` override in compose, same as the old
  single-Dockerfile setup)
- `ghcr.io/sums0907/aarambooks-shopdeck-frontend:main`

`docker-compose.prod.yml` now references only `image:` - no `build:`, no bind-mounts
anywhere.

`mac_to_vps_deploy.sh` no longer does anything git-related on the VPS side. It pushes to
GitHub, watches the Actions run to completion, then SSHes in and does `docker compose pull
&& up -d` against a compose file that lives permanently at
`~/aarambooks/business_systems/shopdeck/docker-compose.prod.yml` on the VPS (placed once,
not via git - see one-time setup note printed at the end of the script).

**To deploy from here on: `./mac_to_vps_deploy.sh "your commit message"` from inside this
repo.** That's the whole workflow now.

## The VPS cutover (already done, verified)

The live `shopdeck-api`/`shopdeck-sync`/`shopdeck-frontend` containers were switched over to
the new images today. Sequence, for reference if you need to repeat or debug it:

1. Fresh Postgres backup taken first: `~/shopdeck_bs_prod_precutover_20260909_130620.dump`
   on the VPS, in addition to the existing Sep-7 backup.
2. `docker-compose.prod.yml` was placed at `~/aarambooks/business_systems/shopdeck/` (the
   old one had already vanished from that path before we got there - see "one open
   question" below).
3. `docker compose pull` + `docker compose up -d`.
4. **`shopdeck-postgres` was never touched** - Compose recognized it as unchanged (same
   image tag, same everything) and left it running (42h+ uptime preserved throughout).
   `shopdeck-api`/`sync`/`frontend` were recreated from the new GHCR images.
5. Verified for real, not just "container is up": `curl
   https://api-shopdeck.aarambooks.cloud/api/v1/system/status` returned
   `{"status":"ok","database_connected":true,"version":"1.0.0"}`, and Postgres row counts
   were confirmed unchanged (8136 `ndr_action_log`, 6344 `customer_info`, 6337
   `order_line_items`, etc. - all real, all intact).

Old locally-built images (`shopdeck-shopdeck-api:latest` etc.) are still cached on the VPS
and were **not** pruned, so there's an instant rollback path if something surfaces that
wasn't caught in verification.

## One open question I couldn't resolve

Before placing the new compose file, the old one was already missing from
`~/aarambooks/business_systems/shopdeck/` - `docker compose ls` still listed it as the
config path for the running containers (Compose caches this per-container, not by re-reading
the file), but the file itself wasn't there to back up. I don't know who/what removed it or
when. Nothing was broken by this (the containers kept running fine off their existing
config), but if you know what happened here, it'd be good to understand - it's the kind of
gap that could bite if it happens again with a file that matters more.

## Your in-flight work (uncommitted right now)

This repo currently has real, uncommitted changes sitting in the working tree:
- Modified: `backend/api/main.py`, `backend/api/routers/orders.py`,
  `backend/sync/start_sync_daemon.sh`, `backend/sync/sync_shopdeck_mcp_data.py`,
  `frontend/src/App.jsx`, `frontend/src/components/StatusBadge.jsx`,
  `frontend/src/screens/Orders.jsx`, `frontend/src/styles/tokens.css`
- New, untracked: `backend/api/routers/insights.py`, `frontend/src/screens/Insights.jsx`,
  `.env.example`

I did not touch, commit, or revert any of this - it's exactly as you left it. The important
thing to know: **none of this reaches the live VPS until it's committed and pushed** (which
triggers the GHCR build) **and then `mac_to_vps_deploy.sh` is run** (which pulls the new
images and restarts). The live containers right now are running whatever was at HEAD
(`db7fbb9`) when the cutover happened today, not this in-flight work.

## Things that are genuinely done, don't redo them

- Repo split (separate git history, separate from Catalog) - done, verified, pushed.
- CI/CD to GHCR - done, verified by watching an actual run complete successfully.
- Bind-mount removal from docker-compose.prod.yml - done.
- VPS cutover to the new images - done, verified against real data and real endpoints.
- Old combined repo archived - done.
