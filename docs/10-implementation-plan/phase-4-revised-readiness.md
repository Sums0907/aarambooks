# Phase 4 Revised Readiness

## Strategic Shift
Phase 4 was originally designed to build Context Adapters for AaramInventory and AaramPacking. Following the ShopDeck schema discovery, this objective is fundamentally invalid. ShopDeck provides the comprehensive operational context, making AaramPacking redundant as a context provider.

## What Phase 4 Should NOW Build
1. **ShopDeck Context Adapter:** A read-only context provider that retrieves `order_summary`, `order_line_items`, and `customer_info` to populate the `CustomerContext`, `OrderContext`, and `ShipmentContext`.
2. **AaramInventory Context Adapter:** A read-only context provider that receives `sku_id`s from ShopDeck payloads and retrieves `quantity_on_hand` to populate the `InventoryContext`. `confidence_score` is explicitly ignored.

## What Phase 4 Should NOT Build
- **AaramPacking Context Adapter:** AaramPacking must be removed from the Context Engine scope. It is strictly an execution system.
- **Any Write Operations:** Adapters must strictly map `GET` endpoints. Brain must not emit actions during context assembly.

## Exact Inputs Required Before Starting
- **Architectural Approval (ADR):** Explicit approval to shift ShopDeck from Phase 5 to Phase 4 and drop AaramPacking context.
- **Authentication Strategy:** An approved mechanism for Brain Core (machine-to-machine) to authenticate against the ShopDeck API and AaramInventory API.
- **Schema Evolution Decision:** A ruling on whether to evolve the Phase 1 models to accommodate ShopDeck's exhaustive fields (`rto_initiated`, `delivery_time`, etc.) or downcast them.

## Expected Files to be Created
- `src/business_adapters/shopdeck_provider.py`
- `src/business_adapters/inventory_provider.py`
- `tests/business_adapters/test_shopdeck_provider.py`
- `tests/business_adapters/test_inventory_provider.py`

## Blockers
- **RESOLVED**: AaramIdentity M2M capability is implemented and available for the Brain → AaramInventory authentication path.
- **RESOLVED**: Phase 4A AaramInventory integration is complete.
- **RESOLVED**: ADR-005 and ADR-006 have been established.
- **BLOCKED**: The remaining Phase 4 implementation blocker is ShopDeck headless connectivity.

## Relationship to Phase 5 and Later
Phase 5 (External Integrations) will no longer include ShopDeck. Phase 5 will strictly handle External Courier/Logistics providers (e.g., Delhivery, BlueDart) to enrich the `ShipmentContext` beyond what ShopDeck natively aggregates.
