# ShopDeck ↔ Brain Context Reconciliation

## Executive Conclusion
**ShopDeck is the primary Operational Context Provider for Aaram Brain.**
The newly discovered ShopDeck payload definitively proves that ShopDeck is the canonical aggregator of customer identity, order lifecycle, payment, shipment tracking, and return/RTO state. 

**AaramPacking is NOT a Context Provider.** AaramPacking is purely a warehouse execution system. Its outputs (e.g., "Order Packed", "RTO Received") are synchronized back to ShopDeck, meaning ShopDeck already contains the authoritative fulfillment state. AaramPacking should be reclassified purely as an **Action Target** for Brain (if at all), but never polled for context.

**AaramInventory remains the sole authority for physical inventory.** ShopDeck holds catalogue definitions, but AaramInventory maintains the double-entry physical ledger (`quantity_on_hand`) and `confidence_score`.

## Source-of-Truth Matrix

| Information | Authoritative System | Evidence | Brain Usage | Brain Owns It? | Notes |
|---|---|---|---|---|---|
| Order State | ShopDeck | `order_summary`, `order_line_items.seller_last_status` | Customer Context | No | Tracks full lifecycle from created to delivered/cancelled. |
| Shipment/AWB State | ShopDeck | `order_line_items.awb_no`, `logistics_reference_number` | NDR/Fulfillment Context | No | |
| Courier/Delivery State | ShopDeck | `delivery_time`, `expected_delivery_date`, `pod_url` | NDR/Fulfillment Context | No | |
| Customer/Product/SKU Context | ShopDeck | `customer_info`, `checkout_events`, `order_line_items` | Customer Context | No | Captures identity, addresses, and full clickstream. |
| RTO/Return State | ShopDeck | `rto_initiated`, `rto_delivered_at`, `return_order_item_id` | Returns/Refund Context | No | |
| Inventory Quantity | AaramInventory | AaramInventory API `GET /read/inventory/balance` | Availability checks | No | Provides `quantity_on_hand`. `confidence_score` is explicitly ignored. |

## ShopDeck → Brain Context Mapping

| ShopDeck field | Business Meaning | Brain Context Field | Required/Optional | Authoritative/Derived | Consumer | Transformation Required |
|---|---|---|---|---|---|---|
| `order_line_items.seller_last_status` | Current fulfillment status | `FulfillmentContext.fulfillment_status` | Required | Authoritative | Brain Core | Direct map |
| `order_line_items.awb_no` | Shipment Tracking ID | `ShipmentContext.tracking_number` | Required | Authoritative | Brain Core | Direct map |
| `order_line_items.customer_last_status` | Public tracking status | `ShipmentContext.status` | Required | Authoritative | Brain Core | Direct map |
| `order_summary.order_id` | Master Order ID | `OrderContext.order_id` | Required | Authoritative | Brain Core | Direct map |
| `customer_info.customer_number` | Customer Phone | `CustomerContext.phone` | Required | Authoritative | Brain Core | Decryption required |
| `order_line_items.sku_id` | SKU ID | `InventoryContext.sku_id` | Required | Authoritative | Context Engine | Used to query AaramInventory |

## The Inventory Boundary

**Recommended Architecture:**
1. Brain retrieves `sku_id` from the ShopDeck order payload.
2. Brain queries AaramInventory (`GET /api/v1/read/inventory/balance`) using the `sku_id`.
3. AaramInventory returns the raw physical truth: `quantity_on_hand` (Note: `confidence_score` is explicitly ignored by Brain).
4. Brain's Context Engine logically derives boolean availability based on rules (e.g., `quantity_on_hand > 0`).

*VERIFIED: This architecture cleanly separates physical truth (Inventory) from logical intelligence interpretation (Brain).*

## The Packing Boundary

**Recommended Architecture:** Option B — Action/Execution system only.
*VERIFIED: AaramPacking exposes execution endpoints (`/packer/labels/{awb}/pack`, `/rto/scan`) but ShopDeck already aggregates the result of these executions into `order_line_items.seller_last_status`.*
Brain does not need to poll AaramPacking for context. AaramPacking should be removed as a Context Provider.

## Identified Conflicts

1. **Conflict:** AaramPacking was scheduled to be a Brain Context Provider in Phase 4.
   - **Classification:** P0 — Architectural contradiction requiring formal decision.
   - **ADR Required:** Yes.
2. **Conflict:** ShopDeck was slated for Phase 5 (External), but it is actually the primary internal context source.
   - **Classification:** P0 — Architectural contradiction requiring formal decision.
   - **ADR Required:** Yes.
3. **Conflict:** Phase 1 Models (`FulfillmentContext`) are too simplistic compared to the exhaustive ShopDeck schema.
   - **Classification:** P1 — Documentation must be corrected.

## Unresolved Questions
- Should Brain downcast the exhaustive ShopDeck tracking fields (`rto_initiated`, `delivery_time`, `courier_allocation_type`) into simplistic Phase 1 context models, or should Phase 1 models be evolved to capture this rich NDR context?
- Given ShopDeck is the primary context, how will Brain authenticate machine-to-machine requests to the ShopDeck APIs/MCP?
