# Plan — rename local folder `aarambooks` → `aaram_brain` (for Gemini to execute)

Written by: Claude (aarambooks workspace)
Date: 2026-09-09
Audience: this plan is written to be run by Gemini, in the Antigravity IDE, since the user
asked for this rename to be executed there rather than by Claude.
Scope: **local Mac only.** This does not touch the GitHub remote, the VPS, or any deployed
container — none of them reference the local folder name at all (verified separately; see
"Non-goals" at the bottom).

## Why this exists

The user asked whether `/Users/sumatidhingra/aarambooks` could be renamed to
`/Users/sumatidhingra/aaram_brain` without repercussions. A check turned up three real
dependencies on the exact path (all local-Mac-only, all fixable) and one genuine unknown that
this plan exists specifically to test empirically rather than assume away.

## What was checked and what depends on the exact path

1. **`/Users/sumatidhingra/Documents/AaramBooks/AaramLauncher/start_all.sh`, line 33**:
   ```bash
   BRAIN_ROOT="/Users/sumatidhingra/aarambooks"
   ```
   Hardcoded. Local dev startup for Brain breaks until this is updated.
2. **`.venv/` inside the repo.** Python virtualenvs bake the absolute path into
   `bin/activate` and the interpreter shebang lines. Survives a rename technically but
   misbehaves subtly (wrong `VIRTUAL_ENV`, tools that check it get confused) rather than
   failing loudly. Cleanest fix is to delete and recreate it, not patch it.
3. **Live processes right now, checked via `ps aux` at the time this plan was written**:
   - Brain's own local dev server is running: `.venv/bin/uvicorn src.main:app --reload --host
     0.0.0.0 --port 8000`, started today. This one process needs to be stopped before the
     rename and restarted after — a `--reload` server watching files inside a directory that
     gets renamed out from under it is at best confusing, at worst simply stops picking up
     changes for the rest of its life.
   - Sibling apps (Inventory `:8100`, a service on `:8200`, Identity-related on `:8001`/`:9000`/
     `:9001`, plus three Vite frontends on `:5173`/`:3100`/`:9001`) are running from **other**
     directories under `/Users/sumatidhingra/Documents/AaramBooks/` — unaffected by this rename,
     don't need to be touched.
   - **An Antigravity IDE language-server process is currently attached to this exact
     workspace**: `workspace_id file_Users_sumatidhingra_aarambooks_aarambooks_code_workspace`.
     This is a live Gemini session open on the old path right now. This is actually useful —
     see Step 0.
4. **Everything else checked and confirmed fine, no action needed**: git itself doesn't care
   about the parent folder name (history/branches/remote all keyed off `.git`, not the path
   above it); the GitHub remote (`github.com/Sums0907/aarambooks.git`) is a separate name from
   the local folder and does not need to change; `.mcp.json` and `.vscode/settings.json` use no
   absolute paths; ~30 hits for the old path inside `patch_*.py`/`fix_*.py`/docs/archived chat
   logs are dead debug scripts and historical text, not live dependencies.

## The one genuine unknown this plan is designed to test, not assume

Gemini's durable memory of this project is known to include the committed transcripts under
`docs/ag_chat_*.md` — plain git-tracked files, completely unaffected by a folder rename. What's
*not* known is whether Antigravity/Gemini also keeps its own internal, IDE-level session memory
keyed by the absolute workspace path (the way Claude Code's own project memory is keyed by
path — a separate, already-confirmed concern on the Claude side, being handled separately by
the user, not part of this plan). Rather than guessing, Steps 0 and 8 below turn this into a
direct before/after test.

## Procedure

### Step 0 — Memory-continuity baseline (do this first, before anything else changes)
In the current, still-open Antigravity session (the one already attached to the old
`aarambooks.code-workspace`), ask Gemini to recall something specific from recent work that
isn't trivially re-derivable from a quick glance at `docs/ag_chat_*.md` — e.g. a specific
decision or number from the ShopDeck/Catalog split work. Write down its answer verbatim
somewhere outside this repo (a scratch note is fine). This is the baseline Step 8 compares
against.

### Step 1 — Stop Brain's local dev server
Find and stop the process currently running:
```
.venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
(however it was started — via `start_all.sh`'s process management, a dedicated terminal tab, or
similar; use whatever `start_all.sh` itself uses to stop things, if it has a stop path, rather
than a bare `kill`, to avoid leaving orphaned child processes). Leave the sibling apps
(Inventory, Identity, ShopDeck, their frontends) running — they're unaffected and don't need to
restart.

### Step 2 — Confirm nothing uncommitted would be lost
```bash
cd /Users/sumatidhingra/aarambooks
git status --short
```
If there's real uncommitted work, commit or stash it (`git stash -u`) before proceeding — a
directory rename itself won't touch working-tree contents, but it's the standard safety check
before any bulk filesystem operation on a repo.

### Step 3 — Close the old Antigravity workspace
Close the IDE window/workspace currently attached to
`file_Users_sumatidhingra_aarambooks_aarambooks_code_workspace` before renaming the directory
out from under it.

### Step 4 — Rename the directory
```bash
mv /Users/sumatidhingra/aarambooks /Users/sumatidhingra/aaram_brain
```

### Step 5 — Fix the hardcoded launcher path
In `/Users/sumatidhingra/Documents/AaramBooks/AaramLauncher/start_all.sh`, line 33:
```diff
- BRAIN_ROOT="/Users/sumatidhingra/aarambooks"
+ BRAIN_ROOT="/Users/sumatidhingra/aaram_brain"
```

### Step 6 — Rebuild the virtualenv
```bash
cd /Users/sumatidhingra/aaram_brain
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 7 — Rename the workspace file (cosmetic, but keeps things consistent)
```bash
cd /Users/sumatidhingra/aaram_brain
mv aarambooks.code-workspace aaram_brain.code-workspace
```
No content change needed inside it — it already uses `"path": "."` (relative), not an
absolute path.

### Step 8 — Reopen in Antigravity and re-run the memory-continuity test
Open `/Users/sumatidhingra/aaram_brain/aaram_brain.code-workspace` fresh in Antigravity. Ask
Gemini the **same** recall question from Step 0. Compare against the written-down baseline:
- **Same/consistent answer** → Gemini's memory isn't broken by the path change; nothing further
  to do on this front.
- **Blank or noticeably different answer** → Antigravity does keep path-keyed session memory,
  and it didn't carry over. Worth deciding at that point whether to manually re-establish
  context for Gemini (e.g. pointing it at `docs/ag_chat_*.md` and recent `docs/claude/*.md`
  files) or treat it as an accepted one-time cost of the rename.

### Step 9 — Restart the local dev stack and verify
Run `start_all.sh` (now pointing at the corrected `BRAIN_ROOT`) and confirm Brain comes up
cleanly on port 8000 alongside the other apps, exactly as before the rename.

## Rollback

Fully reversible, nothing destructive happens at any step:
```bash
mv /Users/sumatidhingra/aaram_brain /Users/sumatidhingra/aarambooks
```
then revert the one line in `start_all.sh` back to the old path, and rebuild `.venv` again if
it was already rebuilt under the new name. No data loss risk at any point — this is a directory
rename plus a one-line config edit plus a virtualenv rebuild, all trivially reversible.

## Non-goals / already confirmed out of scope

- **Not renaming the GitHub repo.** `Sums0907/aarambooks` stays as-is; the local folder name and
  the GitHub repo name are independent, and renaming the GitHub repo would have real
  repercussions (CI, any clone elsewhere, VPS deploy scripts referencing the clone URL) that
  this local rename does not.
- **Not touching the VPS.** Nothing on `aaramhomes@200.234.39.72` references this local Mac
  path — confirmed separately as part of the recent VPS cleanup audit.
- **Not migrating Claude Code's own project-keyed memory** (pinned memories under
  `~/.claude/projects/-Users-sumatidhingra-aarambooks/`). That's a known, separate, already-
  identified consequence being handled directly between the user and the Claude session — not
  part of what Gemini needs to do here.
