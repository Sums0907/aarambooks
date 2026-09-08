# First two physical Gate 3 calls — findings

Author: Claude
Date: 2026-09-08

Two real, self-directed calls were placed (to the operator's own confirmed number, with the
shared queue verified empty of real eligible items both times, so no real customer was ever
at risk). Both calls, and reading their real transcripts, surfaced defects nothing in this
session's testing had found - because nothing before this had actually run against a live
Exotel payload.

## Call 1 — ran entirely stale code

The answering server (`uvicorn`, local machine, reached via ngrok) had been running since
4:03 AM with no `--reload` flag - every fix from this session (mission contract, greeting
rewrite, session_constants extension, writeback auth) existed only as unsaved edits on disk
and was invisible to the running process. Confirmed directly: the greeting was word-for-word
one of the exact hardcoded English strings removed earlier this session. Transcript showed
every anti-pattern the redesign targeted: false "I'm checking" narration, an immediate
English reschedule push, a fabricated COD amount (₹2500 vs the real ₹799), a false "I've
rescheduled it" claim with no backend action ever taken, and the banned "anything else?"
filler loop twice. None of this is evidence against today's work - it's evidence the
process was never restarted. Fixed by restarting with `--reload`.

## Call 2 — two new, more fundamental problems

**The bot is not running our persona.** `bot_id`/`bot_name` in Exotel's platform metadata
say `PRIYA`, identical across both calls - but the bot introduced *itself*, in speech, as
"सुनेहरी" (Sunehri), an older, evidently pre-rename persona (matching a trail of old
`sunehri_*` files elsewhere in this repo). This proves the system prompt actually configured
in Exotel's console is disconnected from `docs/voicebot/bot_persona.txt` and from every
`session_constants` instruction built this session - explaining the still-present "checking"
narration and the hardcoded "I can only offer tomorrow" line, which appeared nearly verbatim
in both calls despite our session never sending such a constraint. **Not fixable from this
repository** - requires opening the Exotel bot-builder console directly.

**The NDR intelligence writeback has never actually run, on any real call, ever.**
`handle_transcript` read `payload.get("transcript")` / `payload.get("TranscriptionText")` -
neither key exists anywhere in Exotel's real payload. The actual customer speech is nested at
`payload["events"][*]["event_data"]["transcript_segments"][*]`, filtered by
`speaker == "customer"`. This meant `raw_transcript` was empty on every transcript event of
both calls (and, by the same logic, every real call before them) - so the classifier, the
one-per-engagement guard, and the ShopDeck POST fixed earlier this session were never once
exercised by real traffic, despite passing every test written against a hand-built payload
shape that never matched reality. `ndr_intelligence_results` was empty and `ndr_queue` stuck
at `call_dispatched` after both calls, consistent with this.

### Fix applied and verified against real data

Added `extract_customer_utterance()` (`src/api/webhooks/exotel_webhooks.py`), which reads the
real nested shape first and falls back to the flat `transcript`/`TranscriptionText` keys only
for this repo's own test/certification payloads. Verified directly against the actual
captured Mongo events from both live calls - correctly extracts `"No, thank you"` and every
other real customer turn. Full suite re-run: identical 18 pre-existing failures, 404 passed -
no regression.

### A real design question this replay surfaced, not yet decided

Replaying call 2's real utterances through the fixed extraction + classifier: the customer
said "I want to reschedule it for day after tomorrow" (classified `RESCHEDULE`, an early
turn), then later - after the bot refused any date but tomorrow - said "okay, you can reset
your late for tomorrow" (also classified `RESCHEDULE`). The one-per-engagement guard claims
the *first* decisive classification, which would record "day after tomorrow" as the agreed
outcome - not what the customer actually settled for by the end of the call. This is a real
trade-off from the "first decisive turn wins" design (chosen to respect ShopDeck's
one-intelligence-result-per-engagement constraint), not a bug in the fix just made. Needs a
deliberate decision: first-wins, last-wins (submit only at session-end using the final
classification), or something else - not something to change unilaterally.

## Still open, unrelated to the above

- No mechanism anywhere in this codebase extracts a specific date ("10th September") beyond
  generic "tomorrow" pattern matching - a real, unbuilt gap, not fixed by anything above.
- What LLM/ASR actually powers the deployed Exotel bot remains unconfirmed - given the
  Sunehri finding, it may not be the `local-qwen` model this session's behavioral harness
  tested against, which would mean that harness's 12/13 result says nothing about what
  customers actually experience.
