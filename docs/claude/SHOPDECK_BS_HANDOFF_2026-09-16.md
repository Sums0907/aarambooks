# Handoff to ShopDeck BS — Brain-side changes, 2026-09-16

Written by: Claude (working on Brain, the AI orchestration service for Aaram Homes'
e-commerce operations). This covers what changed on Brain's side today that touches
ShopDeck BS's data or API contract, what's already confirmed working, and what needs
checking or action on your side.

## Summary

Brain's Sarvam NDR voice-calling pipeline had a working day: two real bugs were found and
fixed in the outcome-writeback path, and a new call-recording capture pipeline (built
recently) got its own same-day reliability fix once tested against real live traffic. None
of this required any schema or endpoint changes on your side beyond what you'd already
built - the `ndr_engagements.recording_url` column and the `PATCH .../queue/{id}/status`
handling for it worked exactly as designed once the bug on Brain's side was fixed.

## 1. Recording capture — confirmed working end-to-end, nothing further needed from you

Background: call recordings are fetched by Brain from Sarvam's analytics API and re-hosted
on Cloudflare R2, then reported to you via `PATCH .../queue/{id}/status` with
`status="call_completed"` and a `recording_url` field, landing on `ndr_engagements.recording_url`.

**Status: confirmed working.** As of now, 23 engagements have `recording_url` populated in
production - the 21 from the historical Sept 15 backfill (thank you for running that SQL)
plus 2 more from today that Brain fixed and backfilled directly. Spot-checked the oldest
row (`eng_f65702563e395fb1b93e75690215fd64`, AWB `142285243279664`) and it carries a real,
working R2 URL with the correct Sept 15 timestamp.

**One thing to know about, not an ask right now**: we noticed your `PATCH .../queue/{id}/status`
handler writes `ndr_engagements.recording_url` *before* it validates the queue-status
transition itself, using a separate connection with no shared transaction. In practice this
means a `recording_url` sent alongside a `status` value that the queue is no longer eligible
for (e.g. the queue already advanced past `call_dispatched`) still gets written, even though
the response comes back as a 409 "Invalid transition." Brain's retry logic currently relies
on this behavior on purpose (a late-arriving recording report still lands even if the queue
moved on in the meantime). This isn't something we need you to change today, but if you ever
refactor that endpoint to wrap both operations in one transaction, a late recording report
would start silently failing to write `recording_url` - worth keeping in mind, and if you'd
rather have a cleaner contract, a dedicated endpoint for setting `recording_url` (decoupled
from the queue status-transition validator entirely) would be the more robust long-term
shape, since a recording isn't really queue state.

**Also worth knowing**: new real calls today did *not* get their recordings captured
automatically - Brain had a bug (recording fetch 404'd because Sarvam's recordings weren't
processed yet at the instant the completion webhook fired) that's fixed but not yet deployed
to Brain's production VPS. Until that deploy happens, don't expect `recording_url` to
populate for new calls in real time - the 23 rows above were all backfilled manually as a
one-off, not produced by the live pipeline yet. We'll let you know once the fix is live.

## 2. Two Brain-side bugs fixed today — informational, no action needed on your side

These were bugs entirely within Brain's own webhook-handling code, already fixed and
deployed to Brain's production VPS. Mentioned here only in case you'd independently noticed
symptoms of either on your end:

- **`address_change_requested`/`phone_no_change_requested` boolean bug**: Brain was checking
  these fields with `== "yes"`, but every real Sarvam call sends them as a genuine JSON
  boolean, not a string. This silently dropped `new_address_details`/`new_phone_number` from
  `action_parameters` on every single real call since the feature was built - fixed now.
  If you've been wondering why those two fields were essentially never populated in
  `ndr_intelligence_results.action_parameters` despite customers giving that information in
  calls, this was the reason.
- **`engagement_registered` queue-status transition skipped on retry**: a retried engagement
  (same `queue_item_id`) could leave `ndr_queue.queue_status` stuck at `claimed` even after a
  real call was successfully placed, because your `/engagements` endpoint's implicit
  status-advancing side effect only fires on a genuinely new registration, not an idempotent
  retry. Brain now explicitly drives the transition itself. If you've seen `ndr_queue` items
  that appear "stuck" at `claimed` despite Brain's logs showing a call was dispatched, this
  was likely why - should no longer happen going forward, but any pre-existing stuck items
  from before this fix would need a manual look if they still matter.

## 3. Real, open ask for your side: `ndr_status` inconsistency

Checked two real calls from today with **identical, correct Brain-side writeback** - both
produced the correct `reschedule_date` in `ndr_intelligence_results`, and both reached
`ndr_queue.queue_status = 'action_ready'` within minutes of each other:

| AWB | `ndr_queue.queue_status` | `shipment_ndr_reports.ndr_status` |
|---|---|---|
| `142285242800562` | `action_ready` | `reattempt_requested` (correctly advanced) |
| `142285242291216` | `action_ready` | still `pending` |

Since Brain's writeback is confirmed identical in shape and timing for both, whatever
consumes an `action_ready` item downstream and updates `shipment_ndr_reports.ndr_status`
seems to have only run for one of the two. Could you take a look at why the second one
didn't advance? Happy to share the exact `ndr_intelligence_results` rows or timestamps if
useful for tracing it.

## Nothing else needed right now

No schema changes, no new endpoints, no other data checks pending on your side beyond the
`ndr_status` item above. We'll confirm separately once the recording-fetch reliability fix
is deployed to Brain's production VPS, so you'll know when to expect `recording_url` to
start populating for new calls automatically rather than via manual backfill.
