# Plan — remove the stray Brain monorepo git clone from the VPS

Written by: Claude (aarambooks workspace)
Date: 2026-09-09
Reviewed by: Claude (ShopDeck workspace), 2026-09-09 — see "Review" section below.
Follow-up by: Claude (aarambooks/Brain workspace), 2026-09-09 — see "Follow-up" section below.
Status: **EXECUTED 2026-09-09, 18:01-18:05 UTC, successfully.** User gave explicit go-ahead
after reviewing the residual-risk callout in "Can this run in autopilot?" below; Steps 1-6 were
then run with a human checkpoint at Step 3 (the destructive step required manual approval
through the tool's own permission gate, separate from the user's verbal go-ahead). Results:
- Backup: `~/aarambooks_full_backup_20260909_180100.tar.gz` (1204 entries, verified non-empty).
- Step 2 pre-flight re-check: 761 tracked files (unchanged from audit), untracked listing
  identical to audit time — safe to proceed, no drift.
- Step 3/3b: all 761 tracked files deleted and confirmed gone (zero `STILL EXISTS` results).
- Step 4: empty directories removed. One harmless artifact — `.github/` and `.github/workflows/`
  survived the first `find -delete` pass (an ordering quirk, not a data issue) and were removed
  manually as a second pass.
- Step 5: `.git` removed. `~/aarambooks/` now contains exactly the four protected folders
  (`business_systems/`, `identity/`, `inventory/`, `packing/`) and nothing else.
- Step 6: full verification passed — all four compose files intact at their original paths, all
  container uptimes consistent with zero restarts caused by this cleanup, all four health
  endpoints returning healthy responses (ShopDeck, Identity, Packing, Inventory).
- Step 7 (expected side effect, not yet observed): whatever was running the recurring `git pull`
  against this checkout will now fail. Per Open Question 1, its identity was never established —
  worth watching for any related error surfacing elsewhere in the next day or so.

## Review — ShopDeck workspace agent, 2026-09-09

Reviewed against everything the ShopDeck workspace has directly observed on this same VPS
today (stale `docker compose ls` labels, silently-failing deploy scripts, directories that
looked fine but were missing files, containers that looked fine but were days stale). Findings,
folded into the procedure below rather than left as a separate list:

1. **The original procedure assumed one continuous shell session.** Steps 2–5 relied on `cd
   ~/aarambooks` from an earlier step still being in effect. That's unsafe if each step is run
   as a separate `ssh user@host "command"` invocation (a fresh shell every time, with no memory
   of a prior `cd`) rather than typed interactively into one open terminal — a very likely way
   for this plan to actually get executed. Fixed: every command below now `cd`s explicitly,
   every time.
2. **`docker compose ls` does not prove a compose file still exists.** It reports the path from
   labels captured when the container was *created* — it never re-reads the file. Verified
   directly on this VPS today: this is what let a deleted-and-never-restored ShopDeck sync
   config go unnoticed. Step 6 (renumbered Step 7 below) now explicitly `ls -la`/`cat`s every
   compose file instead of trusting `docker compose ls`, and now checks all **four** apps —
   the original version checked three and omitted Packing, one of the four folders this plan
   exists to protect.
3. **Open Question 2 ("packing/'s missing compose file") is resolved, not open.** Fixed
   separately today, in the ShopDeck workspace: `~/aarambooks/packing/docker-compose.prod.yml`
   now exists (it didn't when this audit was written), all three Packer containers were
   recreated properly under Compose, and 36MB of uploaded shipping-label files that had *no*
   prior persistent volume were backed up and restored. Practical effect: the "what must
   remain" snapshot below was already stale by the time this plan was written down — `packing/`
   and `identity/` both now hold more than described. That's expected and fine (git-tracked-only
   deletion doesn't care how much untracked content sits alongside it) — it just means Step 2's
   re-check will almost certainly show *more* than the original 6 paths, which is the plan's own
   trigger to stop and re-audit rather than assume nothing changed. Noted inline at that step so
   it isn't mistaken for a sign of trouble.
4. **Open Question 1 (recurring `git pull`) is only partially answerable from here.** This
   ShopDeck-workspace session has never run `git pull` against `~/aarambooks` — every SSH action
   taken here has been `docker`, `nginx`, `psql`, or writing a single file directly. That rules
   this session out as the mechanism. It does **not** rule out the separate, actively-working
   Brain/Catalog session the user has referenced elsewhere in this same conversation (told to
   this agent: Catalog extraction is "being taken care of" by another agent/workspace) — if that
   session holds a persistent terminal or IDE connection to this VPS, it's a fully plausible
   source, and nothing available to this workspace can confirm or rule it out. Still genuinely
   open — do not treat this plan as having resolved it.
5. **No verification that the backup actually succeeded before destructive steps proceed**, and
   **no verification that all 761 files were actually removed before `.git` (the only record of
   which files belonged to the checkout) gets deleted.** `rm -f` suppresses errors by design; a
   permission failure on one file would fail silently and become permanent, unlabeled cruft the
   moment Step 5 removes the metadata that would've identified it. Both gaps now have an
   explicit check added below.
6. **Verification step didn't check container uptime for anything.** Every real deploy failure
   found in this workspace today (Identity, ShopDeck, Packing, independently) manifested as "the
   endpoint looks fine, but the container is days older than it should be" — a health check
   alone would not have caught any of them. Added to the new Step 7.

None of this changes the core approach — delete only git-tracked files via `git ls-files`, never
touch the directory as a whole — which is sound. The gaps were all in execution discipline and
verification depth.

## Follow-up — Claude (aarambooks/Brain workspace), 2026-09-09

Ran Open Question 3's grep (the config-reference check the ShopDeck-workspace review asked for)
before considering this plan ready to execute:

1. **Open Question 3 — resolved, one real lead chased down, no impact found.** The grep turned
   up `identity/docker-compose.prod.yml` referencing a bind-mount device at
   `/home/aaramhomes/aarambooks/infrastructure/secrets/identity` — a path that isn't in this
   plan's known-good folder list. Checked directly: the directory doesn't exist, isn't
   git-tracked, and — confirmed via `docker volume inspect` / `docker inspect` — the actually
   running Identity container doesn't even use it; it's bound to a separate, Docker-managed
   named volume (`identity_identity_keys_data`) instead. This bind-mount definition is stale,
   unused config left over from an earlier iteration. **No impact on this cleanup** (nothing to
   protect — the path doesn't exist and isn't tracked either way), but worth a separate,
   unrelated cleanup of that dead volume definition in Identity's compose file at some point.
   No other config reference outside the four known app folders was found.
2. **Open Question 1 — this workspace is also ruled out.** No persistent SSH connection, cron
   job, or background sync loop against this VPS has been created from this (aarambooks/Brain)
   workspace at any point — every SSH action taken here has been a one-off `ssh user@host
   "command"` invocation for audit or deploy purposes, never a standing connection. Combined
   with the ShopDeck-workspace review ruling itself out, **both known agent workspaces are now
   ruled out**, and the source of the recurring `git pull` is a genuine, unidentified unknown —
   not just an unconfirmed hypothesis. This matters directly for the autopilot question below.

## Why this exists

An unrelated audit (checking who deployed ShopDeck to the VPS) turned up a full git clone of
the `aarambooks` (Brain) monorepo living at `~/aarambooks/` on the production VPS
(`aaramhomes@200.234.39.72`). This directly contradicts the user's stated deployment policy:
no git clones on the VPS, ever — only pre-built Docker images pulled from GHCR, matching how
Identity/Inventory/Packer/ShopDeck are all actually deployed (see
`Aaram_Inventory/mac_to_vps_deploy.sh` as the canonical reference pattern).

The catch: `~/aarambooks/` is *also* the parent directory that holds the real, live deploy
folders for Inventory, Identity, ShopDeck, and Packer (`docker-compose.prod.yml` + `.env` per
app). Those folders are **untracked** by the git clone — they just happen to sit next to it in
the same directory. Any cleanup has to remove only the git-tracked Brain source and leave those
folders completely untouched, since real production containers are managed through them.

## Audit findings (verified directly on the VPS, not assumed)

- `~/aarambooks/.git` — origin `https://github.com/Sums0907/aarambooks.git`.
- **Birth time: 2026-09-07 21:04:40 UTC.** Predates the current Claude session's Brain/Catalog
  work — this was not created by that session's agent.
- Reflog shows ~13 `pull origin main: Fast-forward` events, roughly every 1-24 hours,
  continuously from creation through **today, 11:58:33 UTC** (which picked up this morning's
  "Give Catalog a real HTTP boundary" push). Something with standing SSH access to this VPS is
  running `git pull` there on a recurring basis. The mechanism was NOT identified — no
  systemd timer, no crontab (checked `aaramhomes`'s own; checking others via `sudo crontab -l
  -u <user>` was inconclusive, may have failed silently without a password) accounts for it.
  Leading hypothesis: a separate long-running workstation/IDE session with persistent SSH
  access to this box. **Partially corroborated by the ShopDeck-workspace review above, still
  not confirmed** — see Open Question 1.
- No running container reads from this checkout. Verified via `/proc/<pid>/cgroup` on every
  uvicorn/gunicorn process on the box — all are inside proper Docker cgroups
  (`inventory-api-1`, `shopdeck-api`, `shopdeck-sync`, `shopdeck-frontend`,
  `aaram_identity_backend_prod`, `aaram_identity_frontend_prod`, `packer_*`). Brain itself has
  zero running containers on this VPS — it has never actually been deployed here, consistent
  with prior context.
- `git ls-files | wc -l` → **761 tracked files.** This is the entire Brain source tree: `src/`,
  `tests/`, `scripts/`, `docs/`, `sample-data/`, `archive/`, `scratch_shopdeck_canonical/`,
  `reports/`, `.vscode/`, `.agents/`, `.github/`, root-level `Dockerfile`/`Dockerfile.prod`/
  `docker-compose*.yml`, `litellm_config*.yaml`, `requirements.txt`, `mac_to_vps_deploy.sh`
  (Brain's copy), `pytest.ini`, `.env.example`, plus ~40 one-off debug scripts at the root
  (`check_*.py`, `patch_*.py`, `fix_*.py`, `test_*.py`) and artifacts (`docs.zip`,
  `azm_knowledge.db*`, `uvicorn.log`) that indicate this checkout was used as a live
  debugging/working directory at some point, not just passively cloned and forgotten.
- `git clean -ndx` (dry-run preview of everything untracked+ignored) → **exactly 6 paths at
  audit time**, confirmed to be the real, live deploy folders and nothing else:
  ```
  Would remove business_systems/.DS_Store
  Would remove business_systems/.gitignore
  Would remove business_systems/shopdeck/
  Would remove identity/
  Would remove inventory/
  Would remove packing/
  ```
  **This list is now known-stale as of the review above** — `identity/` and `packing/` both
  gained a `docker-compose.prod.yml` after this audit was written. Re-running this check before
  execution (Step 2) will show more than 6 paths; that's expected, not a red flag, as long as
  every additional path is one of the four known-good app folders.
- `packing/` contains only a `.env` file (344 bytes) — no `docker-compose.prod.yml` next to
  it. ~~Packer's containers... Not investigated further — out of scope for this cleanup~~
  **Resolved, see Review item 3**: this has since been fixed; `packing/` now also has its
  compose file.

## What must remain after cleanup (verbatim from the audit, now updated)

```
~/aarambooks/
├── business_systems/
│   ├── .gitignore
│   ├── .DS_Store          (harmless Mac clutter — optional to delete, doesn't matter either way)
│   └── shopdeck/          (live ShopDeck deploy folder: backend/, frontend/, .env, docker-compose.prod.yml)
├── identity/               (live Identity deploy folder: docker-compose.prod.yml, .env)
├── inventory/              (live Inventory deploy folder: .env, docker-compose.prod.yml, config.prod.js)
└── packing/                (live Packer deploy folder: .env, docker-compose.prod.yml — compose file added 2026-09-09, after the original audit)
```

## What gets removed

All 761 git-tracked files/directories, plus the `.git` directory itself. Nothing untracked is
touched. No `rm -rf` on the whole directory at any point — see procedure below for why that
matters.

## Why not just `mv ~/aarambooks ~/aarambooks.bak`

This was the first plan proposed and the user correctly rejected it: the untracked live deploy
folders (`inventory/`, `identity/`, `business_systems/shopdeck/`, `packing/`) live inside this
same directory. Moving or renaming the whole directory would break every `mac_to_vps_deploy.sh`
script that SSHes in and expects to find its app's `docker-compose.prod.yml` at
`~/aarambooks/<app>/`, for containers that are serving real production traffic right now. Any
cleanup must operate at the file level using git's own knowledge of what it tracks, not at the
directory level.

## Procedure

Every command below is self-contained and re-`cd`s explicitly — do not rely on a previous
command's directory change still being in effect, whether you're pasting these into one open
terminal or running each as its own `ssh aaramhomes@200.234.39.72 "..."` invocation.

### Step 1 — Backup (non-destructive, do this regardless of anything else)
```bash
ssh aaramhomes@200.234.39.72 "tar czf ~/aarambooks_full_backup_\$(date +%Y%m%d_%H%M%S).tar.gz -C ~ aarambooks && ls -la ~/aarambooks_full_backup_*.tar.gz"
```
Backs up everything — tracked and untracked — before anything is touched.

### Step 1b — Verify the backup is real, not just "the command exited 0" (new)
```bash
ssh aaramhomes@200.234.39.72 "tar tzf ~/aarambooks_full_backup_<timestamp>.tar.gz | wc -l"
```
Expect a number in the same ballpark as `761 (tracked) + everything in identity/inventory/
packing/business_systems` — a suspiciously small number (empty or near-empty archive) means the
backup silently failed and must not be trusted before proceeding. Keep this file until the
cleanup has been verified stable for a few days; then it's safe to delete.

### Step 2 — Re-confirm the split immediately before deleting (non-destructive)
```bash
ssh aaramhomes@200.234.39.72 "cd ~/aarambooks && git ls-files | wc -l && git clean -ndx"
```
Expect **761** tracked files (re-check — the repo may have been pulled again since this audit)
and a `git clean -ndx` listing containing **only** paths inside `business_systems/`,
`identity/`, `inventory/`, or `packing/` — nothing else. Per Review item 3, expect *more than*
the original 6 paths (identity/ and packing/ each gained a compose file since the audit) — that
alone is fine. **Do not proceed if anything appears outside those four folders.** If it does,
something changed since this plan was written — stop and re-audit rather than assuming the plan
still applies.

### Step 3 — Delete only git-tracked files
```bash
ssh aaramhomes@200.234.39.72 "cd ~/aarambooks && git ls-files -z | xargs -0 rm -f"
```
This is the core safety property of this plan: it is impossible for this command to delete
anything outside the 761 tracked files, regardless of what else is sitting in the directory.

### Step 3b — Confirm every tracked file actually went (new)
```bash
ssh aaramhomes@200.234.39.72 "cd ~/aarambooks && git ls-files -z | xargs -0 -I{} sh -c 'test -e \"{}\" && echo STILL EXISTS: {}'; echo done"
```
Expect no `STILL EXISTS:` lines before `done`. `rm -f` suppresses errors by design, so a
permission failure on one file would otherwise fail silently — and once Step 5 removes `.git`,
there's no longer any record of which files belonged to this checkout, turning a silent partial
failure into permanent, unlabeled cruft. If anything is listed, stop and investigate (likely a
permissions issue) before continuing.

### Step 4 — Remove directories left empty by step 3
```bash
ssh aaramhomes@200.234.39.72 "cd ~/aarambooks && find . -type d -empty -not -path './.git*' -delete"
```
Re-run `ls -la ~/aarambooks` afterward and manually confirm `business_systems/`, `identity/`,
`inventory/`, `packing/` are still present with their contents intact before continuing.

### Step 5 — Remove the git repo itself
```bash
ssh aaramhomes@200.234.39.72 "cd ~/aarambooks && rm -rf .git"
```
Only run this after Step 3b came back clean.

### Step 6 — Verify nothing broke (rewritten — do not rely on `docker compose ls` alone)
`docker compose ls` reports the compose file path from labels captured when a container was
*created* — it does not re-read the file, so it cannot prove a compose file still exists after
this cleanup. Check the actual files and actual container ages directly, for all four apps, not
just ShopDeck:
```bash
ssh aaramhomes@200.234.39.72 "
echo '--- compose files actually present ---'
ls -la ~/aarambooks/identity/docker-compose.prod.yml
ls -la ~/aarambooks/inventory/docker-compose.prod.yml
ls -la ~/aarambooks/packing/docker-compose.prod.yml
ls -la ~/aarambooks/business_systems/shopdeck/docker-compose.prod.yml
echo '--- container ages (none of these should have changed from before cleanup) ---'
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'identity|inventory|packer|shopdeck'
"
echo '--- health endpoints ---'
curl -s https://api-shopdeck.aarambooks.cloud/api/v1/system/status
curl -s https://api-identity.aarambooks.cloud/auth/public-key -o /dev/null -w '%{http_code}\n'
curl -s https://api-packing.aarambooks.cloud/health
curl -s -o /dev/null -w '%{http_code}\n' https://inventory.aarambooks.cloud/
```
Container ages matching their pre-cleanup values (not reset/restarted) plus every compose file
still present plus every endpoint responding is the actual bar for "nothing broke" — a health
check alone would not have caught any of the real deploy failures found in this workspace today.

### Step 7 — Expected side effect, not a bug
Whatever has been running the recurring `git pull` (unidentified — see Open Questions) will
start failing once the repo is gone. This is expected, but per Review item 4, may not be a loud
or visible failure — if the mechanism turns out to be a silent background loop, "we'll notice
when it breaks" may not hold. Worth a manual check-in with whoever runs the Brain/Catalog
workspace after this runs, not just waiting for an alert.

## Rollback

If step 6 turns up anything broken:
```bash
ssh aaramhomes@200.234.39.72 "cd ~ && tar xzf aarambooks_full_backup_<timestamp>.tar.gz"
```
Restores everything exactly as it was, including the git clone. Since nothing untracked was
ever touched, in practice a rollback should only be needed if step 3/4 accidentally removed
something they shouldn't have — which the `git clean -ndx` pre-check in Step 2 and the
existence-check in Step 3b are specifically designed to catch before it happens.

## Open questions

1. **What is running the recurring `git pull`? Still genuinely open — this is the one thing
   blocking full autopilot.** Ruled out: the ShopDeck workspace (never ran `git pull` against
   this checkout) and the Brain/Catalog workspace (no persistent connection, cron, or sync loop
   was ever created against this VPS from there either — every SSH action from that workspace
   has been a one-off command). Both known agent workspaces are now eliminated, which means the
   mechanism is something neither Claude session is aware of or controls — possibly a human
   terminal session, a third tool, or infrastructure neither workspace has visibility into. If
   it's still expecting `~/aarambooks/.git` to exist when Step 3 runs, deleting it will break
   something for whatever that is, not just produce a harmless, easily-attributed error.
2. ~~`packing/`'s missing compose file~~ — **Resolved**, see Review item 3.
3. ~~Is there any other consumer of `~/aarambooks/<tracked-path>` on the VPS~~ — **Resolved**,
   see the aarambooks/Brain workspace Follow-up above. One reference outside the four known
   folders was found (Identity's stale `infrastructure/secrets/identity` bind-mount definition)
   and confirmed to be dead config with no bearing on this cleanup.

## Can this run in autopilot?

**No — not end-to-end.** Steps 1, 1b, 2, and the Open Question 3 grep are all non-destructive
(backup, dry-run listings, a read-only grep) and are safe to run autonomously; they've already
been run once each while writing this plan, with results folded in above.

Steps 3 through 5 are a different matter: they delete 761 files and the entire `.git` history —
irreversible except via the Step 1 backup, on a VPS that also runs four live production
services. The plan's own safety property (only ever touching git-tracked files) protects
against damaging *those four services*. It does not protect against breaking whatever has spent
two days running `git pull` against this exact repo, on a schedule, for a reason nobody
involved can currently explain. Two independent Claude workspaces have now each checked their
own side and found nothing — which narrows the mystery but does not resolve it. Deleting the
one thing that unidentified process depends on, while it's still a genuine unknown, is exactly
the kind of hard-to-reverse, blast-radius-uncertain action that calls for a human checkpoint
rather than autonomous execution.

**Recommended mode**: autopilot Steps 1/1b/2 (already done), then stop and hand you the actual
results (backup size, current tracked-file count, current `git clean -ndx` listing) for one
explicit go/no-go before Steps 3-5 run. If you'd rather identify the `git pull` source first
(e.g. by checking whatever other terminal, IDE, or script might have a standing connection to
this VPS) that's the more thorough path — but either way, the deletion steps need your explicit
"go" at the time they're about to run, not a standing blanket authorization made now for a risk
that's still unidentified.

## Explicit non-goals

- This plan does not deploy Brain to the VPS. Brain remains undeployed; that's a separate,
  already-flagged piece of work.
- This plan does not touch ShopDeck, Inventory, Identity, or Packer's running containers,
  images, or databases in any way.
- This plan does not attempt to identify or stop the recurring `git pull` mechanism before
  cleanup — it only asks whoever runs this to help rule out whether that mechanism is a hard
  dependency (see Open Question 1) before Step 3 is run for real.
