# Audit — Gemini's test-debris cleanup (`scripts/teardown_test_debris.py`, `inspect_debris.py`)

Reviewer: Claude
Date: 2026-09-08
Status checked: **not yet executed** (dry-run only, confirmed by re-running it myself) - no
data has been deleted. This audit is pre-execution review, not incident review.

## Verdict: solid transactional design, three real coverage gaps. Do not run `--execute` yet.

## What's genuinely good here

This is a marked step up in rigor from earlier in this session. Gemini:
- Actually queried `information_schema` for real FK constraints instead of guessing table
  relationships (confirmed for real: `ndr_engagements` depends on `ndr_queue`,
  `ndr_intelligence_results` depends on both) - this is exactly the discipline that was
  missing when table names were guessed wrong twice earlier in this project.
- Resolves and locks (`FOR UPDATE`) the candidate row set *inside* the same transaction it
  deletes from, closing the discover-then-act race the user's own spec (in the chat log)
  explicitly demanded.
- Defaults to dry-run, uses an exception to force rollback (inelegant but correct with
  asyncpg's transaction context manager), and asserts affected-row counts match the
  pre-resolved set before allowing commit.
- Verified the target database identity (`current_database() == 'shopdeck_bs_prod'`) before
  touching anything - a real, cheap guard against running against the wrong tunnel/host.
- I ran the dry-run myself independently and it produced consistent, sane output.

Also worth noting: Gemini's own `.agents/rules/multi-agent-workflow.md`, written after the
identity/writeback debugging earlier today, explicitly commits to "mock less, run more" and
"treat my own done as a first draft until proven by live data" - and this teardown script's
design (real FK inspection, real dry-run, real transaction discipline) is a concrete
demonstration of that lesson actually being applied, not just stated. Worth acknowledging.

## Three real gaps, verified by running the scripts myself against live data

### 1. The AWB pattern list is already stale and missing live debris

Both scripts hardcode `awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%'`. I queried the
live `ndr_queue` directly and found two rows the pattern does not match:
`AWBGATE302551BA8` and `AWBGATE3CBC022F6` - the AWBs from `certify_gate3_writeback.py`
(the gate-3 writeback verification I ran a few messages ago in this same session). These are
real, current debris that this cleanup will silently leave behind. Running `--execute` today
would report success while missing rows that exist right now.

This isn't a one-time miss - it's structural. Every new certification script picks its own
AWB prefix (`AWBCERT`, `TEST_AWB_`, `AWBGATE3`, and whatever the next one invents), and this
teardown's candidate discovery has no way to know about a prefix it wasn't told about in
advance. A safer discovery query would key off something structural rather than a growing
hardcoded list of naming conventions - e.g. `ndr_queue` rows whose `awb_no` does not exist as
a real shipment in whatever system is authoritative for real AWBs, or a single shared
constant (`TEST_AWB_PREFIX = "TEST_"`) that every certification script is required to use
instead of inventing its own.

### 2. Mongo debris is detected but never cleaned

`inspect_debris.py` explicitly checks MongoDB (`customer_engagements`,
`customer_engagement_events` in the `brain_core` database) for the same synthetic AWBs and
reports what it finds - the chat log confirms Gemini reported "Mongo came back clean for these
IDs" for the current run. But `teardown_test_debris.py` only touches Postgres. If a future
run's Mongo check is *not* clean (a real dispatched engagement did get created for a synthetic
AWB, which is exactly what my own `certify_gate3_writeback.py` run did minutes ago - it
created a real `customer_engagements` document), that debris has no cleanup path at all.
Right now this is silently relying on "Mongo happened to be clean this time," not on the
teardown actually covering both stores it inspects.

### 3. Deletion order is hardcoded, not derived from the graph it just computed

`get_fk_dependencies()` queries and prints the real FK graph, but the actual deletion order
in `run_teardown()` is a fixed sequence written by hand
(`ndr_intelligence_results → ndr_engagements → ndr_queue → order_line_items → customer_info →
shipment_ndr_reports`) that is *not* computed from `deps`. For the two FKs that exist today,
the hardcoded order happens to be correct. But the graph is queried and then not used for
anything except a printout - if a future schema migration adds a new FK (say, something
starts referencing `customer_info`), this script would not know to delete it first, and would
either fail loudly on an FK violation (safe, if the DB enforces it) or - if that new
constraint were somehow not enforced at the DB level - silently leave an orphaned row behind.
Cheap to fix: topologically sort `deps` and delete in that computed order instead of a
hand-written one that happens to currently agree with it.

## One thing NOT to fix, but worth stating explicitly before `--execute`

The script deletes purely by AWB-prefix pattern match, with no `queue_status` or time-based
guard - it would delete a synthetic-prefixed row even if that row were, right now, mid-flight
in a real `call_dispatched` or `action_ready` state. Today that's fine (nothing synthetic is
mid-call), but it's worth being aware this script has no built-in protection against deleting
something someone else's test just dispatched five seconds ago. Given how often this queue
has been touched by concurrent sessions today, a `queue_status NOT IN ('call_dispatched',
'action_ready')` guard in the candidate query would be a cheap, meaningful addition.

## Also flagging, not part of the debris-cleanup ask specifically

`docs/03-intelligence-domains/ndr-intelligence/GATE3-PASS-MASTER.md` (and its duplicate under
`docs/09-decisions/`) is now stale in a way worth correcting before anyone treats it as
current: it predates the `queue_item_id` bug fix and the live gate-3 writeback verification
from earlier in this session, still lists "writeback not verified against a live endpoint" as
an open limitation, and recommends "YES, proceed to Gate 3" conditional on exactly that
verification - which has since happened and passed, but the document doesn't know that. Its
own filename plus an unconditional "YES" recommendation sitting next to a self-acknowledged
unmet prerequisite is close to the exact pattern the user's original instructions warned
against ("do not claim Physical Gate 3 passed merely because..."). Worth a refresh, or a
retire-and-replace, before it's read as the current state by anyone (including Gemini itself
in a future session).

## Recommendation

Fix gap 1 (missing `AWBGATE3%`, and ideally the structural fix so this doesn't recur) before
running `--execute` - as written, execution today would leave two known rows of real, current
debris behind and report success. Gaps 2 and 3 are real but lower urgency: Mongo is
coincidentally clean right now, and the deletion order is coincidentally correct for the FKs
that currently exist. Fix what's provably broken today before running the destructive step;
the other two are worth doing before this script becomes the standing tool for repeated future
cleanups, not necessarily before this one run.

## Addendum — response to Gemini's revised plan (closing the four gaps)

Checked live: both currently-outstanding `AWBGATE3%` rows sit in exactly the two states the
proposed guard would permanently exclude -
`AWBGATE3CBC022F6` = `call_dispatched`, `AWBGATE302551BA8` = `action_ready`. As specified
("add `AWBGATE3%`" + "exclude `queue_status NOT IN ('call_dispatched', 'action_ready')`"),
both fixes land in the same patch and cancel each other out for the exact rows fix #1 was
meant to catch.

This isn't a one-off collision - it's structural. `action_ready` is the normal terminal state
for a *successfully completed* test run (this session's own gate-3 verification proved
exactly that), and `call_dispatched` is where a crashed/failed run gets stuck. A permanent
status exclusion means every future cert run's debris relocates from "eligible forever" to
"action_ready/call_dispatched forever" - never cleaned, just moved to a different
permanently-protected bucket. The guard's real intent (protect something actively in progress
in a concurrent session right now) is a time question, not a status question:
`updated_at > NOW() - INTERVAL '10 minutes'` distinguishes "might still be live" from
"reached this state hours ago and is just sitting there"; a bare status check cannot.

Separately, before the Mongo leg is built: standalone (non-replica-set) MongoDB does not
support multi-document ACID transactions the way Postgres does. The plan says to use "the
same dry-run/execute logic" for Mongo - worth confirming explicitly whether local Mongo here
is a replica set; if not, the Mongo deletes need a verified children-before-parent order
(`customer_engagement_events` before their `customer_engagements` parent) and post-delete
count checks, not an assumed rollback safety net that Postgres has and standalone Mongo does
not.

Last: when refreshing GATE3-PASS-MASTER, keep the queue_item_id bug and its fix in the
record, not just flip "not verified" to "verified." The near-miss (every real writeback would
have posted the wrong ID to ShopDeck) is the most useful part of that story for whoever reads
this document next - losing it to a clean "all green" rewrite defeats the purpose of keeping
the document at all.
