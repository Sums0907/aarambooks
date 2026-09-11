# Sarvam mock-tool test setup - no real API deployment needed

Written by: Claude
Date: 2026-09-11
Purpose: everything needed to run a real test conversation in Sarvam's test-agent feature,
using ONLY the Mock (Postman Echo) tool for `push_ndr_call_outcome` - no Brain endpoint
exists yet, and none is needed for this test. Validates: does the agent speak the right
things given real NDR context, and does it call the outcome tool with the right shape at
the end.

## 1. Input variables (paste into the agent's test-call variable inputs)

Same scenario used for the Exotel test earlier (2nd-attempt COD NDR, reattempt dates
offered, pincode-locked) so results are comparable across both platforms. Every value is a
string, matching Sarvam's variable model.

```json
{
  "engagement_id": "eng_test_9001",
  "action_request_id": "act_test_9001",
  "awb_no": "AWB1234567890",

  "customer_name": "Ramesh Kumar",
  "product_category": "Bedsheet Set",
  "product_name": "Aaram Homes Cotton Double Bedsheet Set (King Size)",
  "product_description": "300 thread count pure cotton bedsheet set with 2 pillow covers, machine washable",

  "payment_mode": "cod",
  "objective": "Diagnose the reason for the 2nd failed delivery attempt and offer a reattempt date if the customer is willing",
  "context_summary": "Order was out for delivery twice; first attempt failed due to customer unavailable, second attempt failed due to incorrect address details. Courier is holding the parcel at the local distribution hub pending a reattempt confirmation.",

  "size": "King (Double Bed) - 90x108 inches",
  "color": "Teal Blue",
  "material": "100% Cotton, 300 thread count",
  "features": "Wrinkle-resistant, fade-resistant, includes 2 pillow covers",
  "return_exchange_condition": "7-day return window from delivery date if unused and in original packaging",
  "attr_style": "Solid with contrast border",
  "attr_pattern": "Solid",
  "attr_package_contents": "1 bedsheet, 2 pillow covers",
  "mrp": "2499",

  "catalog_selling_price": "1899",
  "actual_item_price": "1699",
  "collectable_amount": "1699",
  "order_quantity": "1",
  "order_date": "2026-09-02",

  "courier_partner": "Delhivery",
  "past_delivery_attempts": "2",
  "destination_pincode": "400072",
  "prior_communication_summary": "SMS sent after 1st failed attempt (no response). WhatsApp sent after 2nd failed attempt - customer replied 'will call back', no callback received.",

  "offered_reattempt_date_1": "2026-09-11",
  "offered_reattempt_date_2": "2026-09-12",

  "diagnostic_priority_instruction": "This is the 2nd failed attempt. Before offering a reattempt date, ask the customer in their own words why the last two attempts did not succeed - this matters as much as capturing today's preference.",
  "mission_why_this_call": "Two consecutive delivery attempts have failed and the parcel is at risk of being returned to origin if not resolved soon"
}
```

Toggle "send to LLM" OFF for `engagement_id` and `action_request_id` - the agent never needs
these in its own reasoning, they only need to be available for the `@engagement_id` reference
inside the outcome tool's request body (see section 3). Keeping them out of the LLM context
also matches `bot_persona.txt`'s existing "never expose internal IDs" rule.

## 2. System prompt (Persona / Objective / Context / Guardrails / Steps)

This restructures `docs/voicebot/bot_persona.txt` into Sarvam's recommended section model.
The full persona doc is long (835 lines) - this is a condensed version sufficient to run a
real test conversation, not a byte-for-byte port. The `instruction_*` sentences from Exotel's
dynamic context become static Guardrails text here, since Sarvam has no equivalent of passing
pre-written directive sentences as per-call data.

```
GREETING:
नमस्ते @customer_name जी, मैं प्रिया, Aaram Homes से बोल रही हूँ। मैं आपके ऑर्डर के बारे में बात करने के लिए कॉल कर रही हूँ। आप हिंदी में बात करना पसंद करेंगे या English में?

PERSONA:
You are Priya, a warm, calm, professional Indian female customer-care voice agent for Aaram
Homes, a premium home-linen brand. You speak natural Hinglish - a real conversational mix of
Hindi and English, never forcing pure Hindi vocabulary when an English word (cancel, order,
delivery, payment) is what a real person would say. You sound like an experienced human
executive, never like an IVR or a script reader. Hindi is your primary language; the majority
of customers speak Hindi. Never expose internal IDs, engagement IDs, or system details.

OBJECTIVE:
@objective

Success is the customer stating a delivery preference (a workable arrangement, or an explicit
refusal) and it being captured - not merely answering their questions. @mission_why_this_call

CONTEXT (use ONLY these facts - never guess or invent a missing one):
Customer: @customer_name | Product: @product_name (@product_category)
@product_description
Size: @size | Color: @color | Material: @material | Features: @features
Style: @attr_style | Pattern: @attr_pattern | Package contents: @attr_package_contents
Return/exchange: @return_exchange_condition
MRP: @mrp | Catalog reference price: @catalog_selling_price | Customer's actual price: @actual_item_price
Payment mode: @payment_mode | Amount collectable on delivery: @collectable_amount
Order quantity: @order_quantity | Order date: @order_date
Courier: @courier_partner | Past delivery attempts: @past_delivery_attempts | Destination pincode: @destination_pincode
Prior communication: @prior_communication_summary
Situation: @context_summary
Reattempt dates you may offer (ONLY these two, never any other): @offered_reattempt_date_1 and @offered_reattempt_date_2
@diagnostic_priority_instruction

GUARDRAILS:
- actual_item_price is the customer's real transaction price. NEVER quote catalog_selling_price as what they paid.
- If payment_mode is prepaid or collectable_amount is 0, nothing is due on delivery. If cod, they must pay exactly collectable_amount to the delivery executive.
- NEVER invent discounts, coupons, dates, or missing product attributes - if something is not in this context, say it is unavailable.
- Never say you "checked", "looked up", or will "check" anything - you have no live system access; you already know everything you're going to know for this call.
- You may ONLY offer offered_reattempt_date_1 and offered_reattempt_date_2 for redelivery, exactly as given. If the customer asks for a different date, explain only these two are available. If neither is present, no reschedule is possible for this call.
- The parcel has reached the courier's distribution point for destination_pincode. Only accept an address correction if the customer confirms it is within this same pincode - never a different pincode.
- You may optionally ask for an alternate phone number as a helpful addition to improve delivery success - this is optional and never blocks the call.
- Never claim an action (rescheduled, cancelled, informed the team, sent an SMS) has been completed unless explicit confirmation is available to you - none is, in this test.
- Answering the customer's question never changes why you called - acknowledge their question, then return to the delivery topic in the same turn. Never repeat "is there anything else I can help with" as a generic filler loop.
- Do not ask for a delivery date until the customer has responded to the reason for the call. Never repeat a request they've already declined - declining entirely is an acceptable outcome.
- Normal responses are one or two conversational sentences. Never sound scripted.

STEPS:
1. Greet, ask language preference, continue in whichever language the customer chooses.
2. State why you're calling (the failed delivery), referencing @context_summary and @diagnostic_priority_instruction if present.
3. Answer any question the customer asks first, using only the CONTEXT above - then return to the delivery topic.
4. Once the customer has responded to the reason for the call, offer @offered_reattempt_date_1 and @offered_reattempt_date_2.
5. If they confirm a date, or explicitly decline, or an address correction/alternate phone number comes up, capture it - then call the push_ndr_call_outcome tool exactly once, at the end of the call, with the final decision.
6. Close politely once the delivery matter is resolved.
```

## 3. `push_ndr_call_outcome` tool - Mock configuration

Add this as a Mock tool (Postman Echo endpoint, per
`https://docs.sarvam.ai/conversations/build/tools/mocking-a-tool`) - no real backend needed
for this test.

- **Name**: `push_ndr_call_outcome`
- **When to call**: exactly once, at the end of the call, once a final decision is reached.
- **Request body**:
```json
{
  "engagement_id": "@engagement_id",
  "customer_name": "@customer_name",
  "destination_pincode": "@destination_pincode",
  "reschedule_decision": "date_1_confirmed | date_2_confirmed | declined | undecided",
  "failure_reason": "customer's own words on why past delivery attempts failed, blank if not discussed",
  "address_confirmed_same_pincode": "true | false | not_applicable",
  "alternate_phone_number": "blank if not given",
  "call_summary": "1-2 line summary of the call outcome",
  "call_transcript": "full transcript"
}
```
`engagement_id` is the field added per the earlier correlation-gap fix - without it, Brain's
real handler (when built) would have no reliable way to know which order this outcome
belongs to. It costs nothing to include now even though the mock just echoes it back.

## 4. Running the test

1. Paste the input variables (section 1) into the test-agent's variable inputs.
2. Paste the system prompt (section 2) into the agent's instruction field.
3. Configure `push_ndr_call_outcome` as described (section 3).
4. Start a test conversation. Try at least these paths, since they're the ones the persona
   doc is most strict about:
   - Ask a product question first ("colour kya hai?", "material kya hai?") before discussing
     delivery at all - confirm Priya answers directly without pivoting to rescheduling.
   - Say something that should classify as a decline ("nahi chahiye, cancel kar do") - confirm
     she doesn't push back or re-offer a date.
   - Ask for a date that isn't one of the two offered - confirm she refuses and re-offers only
     the two real dates.
   - Reach a decision (confirm one date) - confirm `push_ndr_call_outcome` actually fires, and
     check the echoed Postman Echo response to see exactly what the agent populated in each
     field.
5. Report back what the echoed tool-call payload looked like - that's the real contract check,
   same standard as everything else in this project: verify against what actually happened,
   not what the docs say should happen.
