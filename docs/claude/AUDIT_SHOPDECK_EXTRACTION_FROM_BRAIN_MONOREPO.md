# Audit: Extracting ShopDeck BS out of the Brain Monorepo

**Status:** Audit only. Nothing implemented. Written in response to the user's four numbered
requirements for relocating `business_systems/shopdeck` out of `aarambooks` and into a standalone
location/repo.

## The single most important finding

**The target location is not empty and this is not a fresh extraction — it's a reconciliation.**

`/Users/sumatidhingra/Documents/AaramBooks/business_systems/` is already a real git repository:

```
remote: https://github.com/Sums0907/aarambooks-business-systems.git
branch: main, up to date with origin/main
tracked top-level: .gitignore, catalog/, shopdeck/
```

It contains a **mature `catalog/` business system** (15 real commits — concurrency-safe reservation
triggers, publication lease state machine, adversarial test suites) that has nothing to do with
this task and must not be disturbed.

Its `shopdeck/` subtree's last real commit is `65741cd feat: complete ShopDeck Business System —
API, frontend, auth, sync engine` — from an earlier, since-superseded flat `backend/api/*` → `api/*`
layout. Since then, someone has been dropping newer files into the working tree **without
committing**: `git status` there currently shows dozens of files as "deleted" (the old `api/*`
layout no longer exists on disk) and an entire untracked `backend/` directory sitting alongside it.
I diffed that untracked `backend/` against today's current `aarambooks` copy — it's missing:

- The new `ndr_queue.py` endpoints/repository/schema work from this session
- The entire `backend/domain/` directory (your concurrent work with Gemini)
- `test_classifier.py`
- Current versions of `auth.py`, `main.py`, `repositories/ndr.py`, `repositories/ndr_queue.py`,
  `schemas/ndr.py`, `schemas/ndr_queue.py`, `services/ndr.py`, `sync_shopdeck_mcp_data.py`

**Conclusion: `/Users/sumatidhingra/aarambooks/business_systems/shopdeck` is the only complete,
current source of truth.** Both the stale `Documents/AaramBooks/business_systems/shopdeck` (this
repo) and the separate `Documents/AaramBooks/business_systems/shopdeck` frontend-only duplicate I
found in an earlier turn (byte-identical `frontend/src`, no `.git` of its own) are behind it.

**This also means requirement #4's premise needs revisiting**: you asked for git/deployment
"separately for shopdeck," but the repo that already exists at the target path is a
**multi-business-system repo** (`business_systems` root, `catalog/` + `shopdeck/` as siblings), not
a shopdeck-only repo. Your requirement #5's target path (`.../business_systems/`, not
`.../business_systems/shopdeck/`) is consistent with that — I'm treating "shopdeck lives inside the
existing `aarambooks-business-systems` repo, alongside catalog" as the intended shape. **Flag if
that's wrong** — a shopdeck-only repo is a different, larger piece of surgery (new GitHub repo, new
remote, no shared `.gitignore`/workspace with catalog).

## Runtime coupling audit: Brain ↔ ShopDeck

Good news — **this is a clean HTTP boundary already, not a code-import boundary.** Confirmed by
grepping both directions:

- **Brain → ShopDeck: zero Python imports.** Every hit for `business_systems.shopdeck` inside
  `src/` is a comment or docstring (e.g. `ccc_builder.py`, `shopdeck_cem_adapter.py`,
  `exotel_webhooks.py` — all just reference shopdeck file paths in prose). The actual integration
  is `ShopdeckCemAdapter` calling out over HTTP to `settings.shopdeck_url`
  (`src/shared/config.py:34`, env var `SHOPDECK_URL`, currently
  `https://api-shopdeck.aarambooks.cloud` in the root `.env` — the VPS production URL). This is
  config, not code — moving shopdeck's source doesn't touch it.
- **ShopDeck → Brain: one deliberate webhook, also config-based.** `backend/sync/
  sync_shopdeck_mcp_data.py:422` POSTs `{awb_nos, source}` to `{AARAM_BRAIN_URL}/events/ndr`
  whenever new NDR reports sync in, wrapped in a non-fatal try/except. Controlled by the
  `AARAM_BRAIN_URL` env var in `docker-compose.prod.yml`. Also config, not code.
- **ShopDeck code importing Brain's `src.*`: none found**, except three loose patch scripts (below)
  that hardcode the current absolute path, and a false-positive grep match inside a test file's own
  self-referential path string.

**Practical implication: the "ripping apart" is almost entirely a git/filesystem exercise, not a
refactor.** As long as both env vars (`SHOPDECK_URL` on the Brain side, `AARAM_BRAIN_URL` on the
ShopDeck side) keep resolving to real reachable URLs after the move, the running systems don't care
where the source code lives on disk.

## Database continuity audit (requirement #3)

Confirmed low-risk. ShopDeck's own `.env` has:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod
```

Port `5434` is the **Brain's own dev Postgres container** (`aarambooks-brain-db-dev`, confirmed via
`docker ps`) — ShopDeck's local dev database is a distinct database name (`shopdeck_bs_prod`,
confusingly named — it's the dev database despite the name) living inside that same shared Postgres
server. This is a pure network connection string with **zero dependency on where the ShopDeck
source code physically lives** — moving files doesn't touch it. I diffed this value between the
current `aarambooks` copy and the stale `Documents` copy: **identical**. This is a separate axis
entirely from `SHOPDECK_URL` (Brain's route *to* ShopDeck's API, which does point at the VPS) — no
risk of the two getting confused as long as whoever does the copy carries `.env` over verbatim
rather than reconstructing it from a template.

**Verification step for whoever executes this:** after the move, boot the relocated backend and
confirm `ndr_queue` row count is still 2 (today's real count) — proves it's the same physical
database, not an empty new one.

## Debris found (needs your decision before anyone touches it)

1. **`scratch_shopdeck_canonical/` — 83MB, git-tracked, at the Brain repo root** (not under
   `business_systems/`). A full parallel copy of shopdeck-like backend/sync code (`mcp_client.py`,
   `mcp_auth.py`, `sync_shopdeck_mcp_data.py`, its own `test_ndr_queue.py`). Last touched by commit
   `585abbf Fix update_queue_status missing claimer_id`. Given its size and git history, I did not
   inspect its full contents or delete anything — **you should say whether this is disposable
   scratch or something to archive** before it's touched.
2. **Three patch scripts at `business_systems/shopdeck/` root**, dated Sep 8 (today's session,
   likely used to apply an earlier code patch programmatically): `patch_repo.py`, `patch_repo2.py`,
   `patch_router.py`. Each hardcodes `/Users/sumatidhingra/aarambooks/business_systems/shopdeck/...`
   as an absolute path. Not part of the app — recommend leaving these behind (not copying them to
   the new location) rather than carrying forward dead scripts with a now-wrong path.
3. **`setup_test_db.py`, `setup_test_db2.py`, `vps_test.py`** — also loose at the shopdeck root,
   also look like one-off dev/debug scripts rather than shipped app code. Recommend reviewing each
   before deciding whether it travels to the new location.
4. **Seven scratch/certification scripts at the Brain repo root** reference "shopdeck":
   `check_postgres_db.py`, `test_e2e_cert2.py`, `db_cert.py`, `test_e2e_cert.py`,
   `check_mcp_schema.py`, `copy_db.py`, `test_api.py`. These will likely become orphaned/stale once
   shopdeck's source moves out from under them — worth a pass to confirm none of them are still
   load-bearing (e.g. referenced by a CI step) before the move, not after.
5. **Comment/docstring references** to `business_systems/shopdeck/...` paths in
   `src/intelligence_domains/ndr/reply_parser.py`, `src/api/webhooks/exotel_webhooks.py`,
   `src/workers/outbound_writeback_worker.py`, `src/infrastructure/adapters/shopdeck_cem_adapter.py`,
   `src/infrastructure/adapters/customer_engagement/repository.py`,
   `src/brain_core/context_engine/ccc_builder.py`. Purely cosmetic — nothing breaks, the comments
   just go slightly stale. Low priority, fix opportunistically if you're already touching those
   files for other reasons.

## `mac_to_vps_deploy.sh` verdict: **not ready as-is**

The local half is fine unchanged — `git add .` / `git commit` / `git push origin main`, run from
inside the new repo's `shopdeck/` subdirectory, will correctly scope to just that subtree (`git add
.` is cwd-scoped) and push to `origin` (already correctly set to `aarambooks-business-systems`).

The **VPS half hardcodes the monorepo layout** and will not work unmodified:

```bash
cd ~/aarambooks              # assumes the VPS checkout root IS the Brain monorepo
git pull origin main
cd ~/aarambooks/$APP_FOLDER  # APP_FOLDER="business_systems/shopdeck"
```

If the standalone repo becomes the deployment source, this needs:
- A **new** clone of `aarambooks-business-systems` on the VPS at a new path (e.g.
  `~/aarambooks-business-systems` — needs a decision), separate from the existing `~/aarambooks`
  checkout that's currently serving live production traffic.
- `APP_FOLDER` changes from `"business_systems/shopdeck"` to `"shopdeck"` (business_systems is now
  the repo root, not a subdirectory needing that prefix).
- The `cd ~/aarambooks` lines repointed to the new clone path.

**This is a production cutover, not a config edit.** The VPS is currently serving
`api-shopdeck.aarambooks.cloud` from the old monorepo checkout. Recommend: stand up the new clone
+ build on a non-production port first, verify it serves identically, *then* cut the real deploy
path over — not a same-session flip. I can't verify from here whether a reverse proxy / DNS config
outside this repo also needs repointing to a new path — that needs checking on the VPS directly.

## Workspace file audit (requirement #5)

- `aarambooks.code-workspace` (Brain root, untracked, new today) — currently just `{folders:
  [{"path": "."}]}`, i.e. points at the Brain monorepo only.
- `business_systems/shopdeck/shopdeck.code-workspace` (gitignored, so it's meant to be
  personal/local) — also just `{"folders": [{"path": "."}]}`, points at shopdeck's current location.
- **No workspace file exists yet** at `/Users/sumatidhingra/Documents/AaramBooks/business_systems/`.
- Per your stated end state, a new workspace file at that path (folders: `.` for the whole
  business_systems repo, so both `catalog/` and `shopdeck/` are visible) is what "this workspace
  should point to the new business_systems" implies. Decide whether `aarambooks.code-workspace`
  stays as a separate Brain-only workspace for when you need to work on Brain, or gets retired.

## Proposed phase order (once you've answered the open questions above)

1. **Decisions from you**: scratch_shopdeck_canonical disposition, the 7 root scratch scripts,
   confirm "shopdeck lives inside the existing multi-system repo" reading is correct, and whether
   monorepo git history for the shopdeck subtree should be preserved (heavier — `git subtree
   split`/`filter-repo`) or the current state becomes a fresh baseline commit in the target repo
   (simpler; the target repo's own shopdeck history is already incomplete anyway, so little is lost).
2. **Quarantine the stale copy** (your requirement #1): inside the `aarambooks-business-systems`
   repo, `git rm -r --cached shopdeck/` (stop tracking, keep history), then physically move the
   directory to `Documents/AaramBooks/business_systems-old/shopdeck-old` (outside any repo — pure
   filesystem, since that's a sibling of `business_systems`, not inside it), commit the removal.
3. **Fresh copy-in** (requirement #2): copy (not move yet) the current, complete
   `aarambooks/business_systems/shopdeck` into the now-empty
   `Documents/AaramBooks/business_systems/shopdeck` slot, excluding the debris flagged above unless
   you say otherwise. Commit as a clean baseline in the target repo. Verify it builds/boots there
   before touching the original.
4. **Database continuity check** (requirement #3): confirm `.env` carried over verbatim, boot the
   relocated backend, confirm it reports the same real row counts as today (not a fresh empty DB).
5. **Remove from the monorepo**: only after step 3 is verified working, `git rm -r
   business_systems/shopdeck` inside `aarambooks` itself, as its own commit, in its own repo —
   satisfies "aarambooks should not have business_systems/shopdeck."
6. **Deployment cutover** (requirement #4): update `mac_to_vps_deploy.sh`'s VPS-side paths as
   described above, stand up a parallel non-production deployment on the VPS from the new repo,
   verify parity, then cut the real path over.
7. **Workspace** (requirement #5): create the new `.code-workspace` at the `business_systems` root;
   decide the fate of the Brain-only one.

I have not implemented any of this. Say which of the open decisions in step 1 you want to make, and
whether the phase order above is the sequence you want, before anything gets touched.
