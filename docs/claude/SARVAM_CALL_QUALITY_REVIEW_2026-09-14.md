# Sarvam call quality review — first 5 real dispatches (2026-09-14)

Written by: Claude, 2026-09-15
Addresses the "review real call quality" item flagged as urgent in
`CONTEXT_HANDOFF_SARVAM_MIGRATION.md` (next-steps item 10).

## Scope and an important caveat

Source: raw `interaction_transcript` and `final_agent_variables` from the 5
`call-completed` webhook events logged in Brain's own Mongo
(`aarambooks_ndr_communications.customer_engagement_events`) on 2026-09-14, matched against
their `customer_engagements` records. Full transcripts are in the appendix below.

**These calls ran through `TEST_PHONE_OVERRIDE`** (removed from the VPS on 2026-09-15, after
these calls happened) - every one landed on the user's own test number, not a real customer.
The person answering was clearly deliberately stress-testing the bot (asking it to switch to
Punjabi/Kannada, reciting random digits, asking "are you crazy?", commenting on its speaking
pace). Treat this as a stress test that surfaced real behavior under adversarial probing, not
as organic customer sentiment - the "customer intent" data below (cancellations, disputed
order quantities) does not reflect a real customer's real situation.

## Calls reviewed

| engagement_id | AWB | status | duration | call_outcome |
|---|---|---|---|---|
| eng_40728a75... | 24899810621600 | connected | 300.3s (hit cap) | rescheduled |
| eng_222f6b99... | 24899810620513 | connected | 300.4s (hit cap) | customer_declined |
| eng_27966a8c... | 24899810620653 | busy | - | (never connected) |
| eng_21c03e4e... | 372194775829 | connected | 156.0s | customer_declined |
| eng_c60f735b... | 24899810621740 | connected | 142s | escalation_requested |

## Findings, most actionable first

### 1. Two of four connected calls were hard-cut at the 300-second cap, mid-conversation, with no goodbye
Both `eng_40728a75...` and `eng_222f6b99...` run exactly ~300.3-300.4 seconds and their
transcripts simply stop after the agent's last line - no closing line, no "is there anything
else," nothing. Compare to the two shorter calls (156s, 142s), both of which end with a
proper wrap-up line ("thank you for your time... Namaste!"). This means a real customer stuck
in an unproductive loop with the bot would experience an **abrupt disconnection**, not a
graceful hangup. There's no stall/loop detection to end a going-nowhere call early and
gracefully - worth adding before wider real-customer rollout, since this is the single
worst experience a real customer could have (call center customer service is quite hard to make and the delivery/NDR flow means it's especially your existing customers).

### 2. The bot re-anchors to "should I fix the delivery date" after almost every single reply, and a caller explicitly complained about it
In `eng_40728a75...`, the agent appends some variant of "should I fix the delivery date"
after answering nearly every tangential question (12+ times across the call). The caller
directly called this out: *"Why are you focusing on this delivery reschedule again and
again? Can I not ask more questions?"* This is exactly the kind of repetitive, robotic
pattern the handoff doc's still-pending "full persona port" (response-length discipline,
from `docs/voicebot/bot_persona.txt`) was meant to fix - this is now a real, observed
instance of that gap, not a theoretical one.

### 3. The bot accepted contradictory order-quantity claims without pushback, and "noted" them
In `eng_222f6b99...`, the caller claimed the order was for 1 bedsheet (system says 2), then
immediately re-claimed it was 3, and the bot responded "Okay, sorry, meaning you had ordered
three sets. I will note it down right now" both times - no cross-check against the real order
data it already has, no pushback on the inconsistency. If "noted" claims like this feed into
any downstream action (refunds, order corrections) without a human or a data-verification
step in between, this is a real manipulation surface - a caller can get false claims "on
record" just by asserting them repeatedly. Worth confirming what actually happens to a
`call_summary`/note like this downstream.

### 4. The reschedule window is narrow and has no real fallback for genuine unavailability
The bot only ever offers the next 2 calendar days (matching the documented
`reschedule_window_days` policy) and firmly refuses anything else - a caller in
`eng_222f6b99...` said *"I might not be available on these 2 dates"* and the bot's only
answer was "I'll note it down, team will reach out separately." For attempt 1/2 NDRs this is
the deliberate policy, but it means any customer with a real scheduling conflict on both
offered days cannot complete a booking through the bot at all - worth knowing this is a real,
now-observed limitation, not just a hypothetical edge case.

### 5. Two of four calls ended in an explicit cancellation request, bucketed under the generic `customer_declined` outcome
Both `eng_222f6b99...` and `eng_21c03e4e...` had the caller explicitly ask to cancel the
order. Both got `call_outcome=customer_declined` - there's no distinct
`cancellation_requested` outcome in the enum. Worth confirming a real downstream process
actually picks up `customer_declined` calls and acts on an explicit cancellation ask,
since it's being asked for by name in the transcript, not left ambiguous.

### 6. Things that worked correctly
- **Courier partner name was never revealed**, across all calls - matches the directive
  constraint and held up under direct questioning ("Can I ask which courier company is
  delivering this?").
- **Pincode changes were correctly refused** with a real, coherent reason ("the courier can
  only deliver in the area for which the order was booked"), while same-pincode address
  changes were correctly offered.
- **Phone number capture verified itself properly**: caller gave a truncated number
  ("Seven nine double eight"), the bot caught that it was only 4 digits and asked for the
  full 10, then read the captured number back digit-by-digit for confirmation.
- **The escalation case (`eng_c60f735b...`) was handled well**: caller wouldn't commit to a
  date without fabric confirmation from a human team; the bot didn't hallucinate fabric
  details, correctly deferred, and got `escalation_requested` - this is the fallback working
  as intended.
- **Language switching functioned** on request (Hindi, claimed Punjabi/Kannada support) -
  though this can only be confirmed from the English-rendered transcript text here; actually
  listening to the audio would be needed to judge real pronunciation/fluency quality.

### 7. Minor, recurring: pace complaints
Two of four callers explicitly asked the bot to slow down. Could be a Sarvam TTS speed
setting rather than a script issue - worth a quick check regardless since it came up twice
out of four calls.

## Suggested priority if addressing before wider rollout
1. Stall/loop detection + graceful call-ending before the 300s hard cap (finding 1) -
   highest priority, this is what a real customer would notice most.
2. Reduce the "redirect to primary objective" repetition frequency (finding 2) - part of
   the pending full persona port anyway.
3. Confirm what happens downstream to a `customer_declined`/cancellation call and to
   "noted" claims like disputed order quantities (findings 3 and 5) - not a Brain-code fix,
   a process/ownership question.
4. Reschedule-window fallback for genuine unavailability (finding 4) - a policy decision,
   not a bug.

## Appendix: full transcripts

See `eng_40728a75...` through `eng_c60f735b...` above for engagement IDs. Full transcripts
were extracted directly from `customer_engagement_events.payload.interaction_transcript` in
Brain's Mongo and are available on request - not duplicated in full here to keep this doc
focused on findings; the source JSONL dumps are on the VPS Mongo container, not persisted
elsewhere.
