# URGENT — order_line_items duplication is corrupting live NDR calls

Written by: Claude, working on Brain (Aaram Homes' AI orchestration service). This affects
real customers on live calls happening right now — please treat as high priority.

## The bug, in one sentence

`GET /api/v1/ndr/{awb}`'s item query (`api/repositories/ndr.py`, `get_order_items`,
line 95-107) reads raw rows straight out of `order_line_items` with no deduplication, but
`order_line_items` is documented in your own sync code as an **append-only event log** ("one
row per (line item, status snapshot)" — `sync/sync_shopdeck_mcp_data.py` line 59-60), not a
current-state table. Every time your sync job re-fetches a line item and sees any changed
`updatedat`, it appends a new row — same product, same quantity, same price, same SKU — even
when nothing about the line item actually changed. `get_order_items` returns every one of
those snapshots as if each were a distinct real item.

## Real, measured scope — not an edge case

Checked every AWB currently in `ndr_queue` with more than one `order_line_items` row:

```
multi_row_awbs      : 180
pure_duplicates      : 178   (same SKU/product/qty/price repeated N times)
genuinely_distinct   : 2     (actually different SKUs - a real clubbed order)
total_duplicate_rows : 2244
```

**178 of 180 is not an edge case — it's the default outcome whenever an order has more than
one snapshot in this table.** Genuine multi-SKU clubbed orders are the rare case, not the
common one.

## What this does downstream, concretely

Brain's context builder (`ccc_builder.py`) sums `quantity` and joins `product_name` across
whatever `items` list this endpoint returns, specifically to handle real clubbed orders. Fed
duplicate snapshots instead, it produces exactly the corrupted output already reported to
you once as an isolated issue (AWB 24899810621740) — turns out to be systemic. Real,
currently-stored payload sent to the voice agent for that AWB:

```json
{
  "collectable_amount": 3580,      // real order was ₹1790 - one bedsheet
  "actual_item_price": 1790,
  "order_quantity": 2,              // real quantity was 1
  "product_name": "1x Golden Sunshine Mustard Floral Frills Bedsheet Set - with 2 Cushions, 1x Golden Sunshine Mustard Floral Frills Bedsheet Set - with 2 Cushions"
}
```

Two identical rows for SKU `127BS`, `quantity: 1` each in the underlying table - this is not
a real 2-unit order. The AWB with the worst case found so far (`24899810630346`) has **37**
duplicate rows for a single real product.

**On a live call, this means**: the agent states a COD collectable amount roughly double
(or more) the real one, and reads back a garbled, repeated product description. Every
one of the 178 affected AWBs going through NDR right now carries this risk.

## What needs to happen

`get_order_items` needs to collapse to one row per genuine physical line item, keeping only
the latest snapshot for each — a `DISTINCT ON` (or equivalent) keyed to whatever uniquely
identifies one real line item in your schema (not `updatedat`, since that's exactly the
column that changes across snapshots of the same item). You know the table's actual grain
better than a query-only read can tell me — I'd rather point at the precise defect than
guess the wrong dedup key and send you chasing the wrong fix.

Separately, for the 2 AWBs that ARE genuinely distinct multi-SKU orders: worth confirming
your intended source-of-truth query elsewhere in the codebase (order confirmation emails,
invoices, etc.) already dedupes this table correctly - if `get_order_items` is the only place
reading this table's raw rows, other read paths may have the identical exposure.

## Why this matters more than a typical data-quality bug

This isn't a display glitch. It's stated out loud, by an AI voice agent, to a real customer,
as the amount of cash they owe on delivery. Worth prioritizing over the other open items in
the existing handoff doc.
