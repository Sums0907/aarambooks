# Senior Review — "Close the remaining gaps" plan (Gemini)

Reviewer: Claude
Date: 2026-09-08
Subject: Gemini's plan to close the four items my implementation report left open.

**Verdict: items 1, 2, 4 reasonable. Item 3 targets tables that do not exist in this schema —
verify before executing or it will burn a cycle chasing the wrong names.**

## Item 3 — De-mocking `certify_gate2.py`: wrong table names

The plan says: *"insert the synthetic AWB into `shipments`, `shipment_items`, `customers`."*
Those tables are not in this codebase. Tracing the actual hydration path
(`src/infrastructure/adapters/shopdeck_cem_adapter.py` -> ShopDeck's
`GET /api/v1/ndr/{awb_no}` -> `NDRService.get_shipment_ndr_context` ->
`business_systems/shopdeck/backend/api/services/ndr.py:14`) shows the real dependencies are:

- **AWB existence check**: `repository.check_awb_exists(awb_no)` against **`order_line_items`**
- **NDR operational state**: `repository.get_shipment_ndr_report(awb_no)` against
  **`shipment_ndr_reports`**
- **Order items / COD amount**: `repository.get_order_items(awb_no)` — also against
  `order_line_items`, by the field names it maps (`sku_id`, `product_id`,
  `customer_product_short_id`, `cod_charge`, `delivery_fees`)
- **Customer phone**: joined from **`customer_info`** (confirmed separately in
  `ndr_queue.py`'s enrollment query: `INNER JOIN (SELECT DISTINCT awb_no, customer_number
  FROM customer_info ...)`

So the four tables to seed are `order_line_items`, `shipment_ndr_reports`, `customer_info`,
and whatever backs `get_ndr_action_history` (optional — the service treats an empty history
as an empty list, not a failure). `certify_gate2.py` already seeds `shipment_ndr_reports` and
`ndr_queue` directly; it is missing `order_line_items` and `customer_info` rows for the
synthetic AWB, not the three tables named in the plan.

## Two more things Q1 (my earlier round-2 review) didn't have visibility into

**`check_awb_exists` will 404 the synthetic AWB even with `shipment_ndr_reports` seeded.**
`get_shipment_ndr_context` calls `check_awb_exists` against `order_line_items` *first*, before
ever reading `shipment_ndr_reports`. Today's `certify_gate2.py` never inserts into
`order_line_items`, so the real hydration path 404s regardless of what `ndr_queue` or
`shipment_ndr_reports` contain — that's the actual mechanism behind the `DummyCCC` mock's
existence, not a vague "synthetic AWBs 404" as I put it in round 2.

**The claim response and the mission factory now agree, but this was a real bug until just
now.** Separately from this plan review: `mission_factory.build_ndr_mission` was reading
`ndr_count_at_enroll` — the raw Postgres column name used only at enrollment
(`repositories/ndr_queue.py:48`) — but `NDRClaimResponse`, the schema actually returned to the
poller, serializes that value as `ndr_attempt_seq`
(`schemas/ndr_queue.py:16-24`, no `ndr_count_at_enroll` field exists on it). In production this
meant `.get("ndr_count_at_enroll")` always returned `None`, so the "this order has had N failed
delivery attempts" clause in `why_this_call` never rendered. My own test didn't catch it
because the test fixture used the same wrong key the code used, so it validated the code
against itself rather than against the real contract. Fixed just now
(`src/intelligence_domains/ndr/mission_factory.py`, `tests/test_ndr_mission_contracts.py`) —
19/19 still pass. Noted here so anyone reading this plan alongside my implementation report
isn't working from stale information about what the queue item actually contains.

## Items 1, 2, 4 — no objection, two small notes

**Item 1 (LLM behavioral harness).** Using `docs/voicebot/bot_persona.txt` as the real prompt
template is the right call — it exists locally and is presumably the actual persona Exotel is
configured with, not a guess. Confirm it is in fact byte-for-byte what's loaded into the Exotel
console today; if the console prompt has since diverged from this file, the harness tests a
prompt Priya never actually runs. Worth a one-line confirmation before treating harness passes
as evidence.

**Item 2 (writeback E2E test).** "Live ShopDeck DB" should mean the local Postgres this repo's
docker-compose brings up, not literally the production database — confirm that's the intent
before anyone runs it, given the plan is silent on which environment.

**Item 4 (remove hardcoded phone).** The plan's fallback ("or extract phone from queue_item if
provided by ShopDeck during claim") won't work as stated: `NDRClaimResponse` does not carry
phone directly — this is the same class of error as item 3. Phone is available at hydration
time via `ccc.customer_profile.phone` (already computed in `ccc_builder.py`), not at claim
time. `DummyAction.parameters["customer_phone"]` is only used before hydration; check what
actually consumes it before rewriting — if hydration's phone is what dispatch uses downstream,
the DummyAction value may already be dead code rather than something needing a data source.

## Recommendation

Correct item 3's table list (`order_line_items` + `customer_info`, not `shipments` /
`shipment_items` / `customers`) and item 4's phone source before executing. Items 1 and 2 are
fine to proceed with the confirmations above.
