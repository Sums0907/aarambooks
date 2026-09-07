# AZM Universal Contract Ingestion Certification

## Executive Summary
This document certifies that the AZM architecture has been corrected, unified, and verified against its required architectural invariants. The legacy Business-System-specific ingestion pipelines (`catalog_ingester.py` and `shopdeck_ingester.py`) have been entirely replaced by a single, generic `contract_parser.py`. Both the Catalog and ShopDeck Business Systems now successfully export their knowledge to AZM using the unified Markdown Contract Grammar.

## Certification Criteria Addressed

### 1. P0 Architectural Purity Verified
- **No BS-Specific Parsers:** `catalog_ingester.py` and `shopdeck_ingester.py` have been deprecated and removed. All ingestion is performed by `contract_parser.py`.
- **Parser Agnosticism:** `contract_parser.py` was audited using `grep` and contains zero hardcoded references to `shopdeck`, `catalog`, or any other Business System.
- **Unified AZM Pipeline:** The canonical architecture (`Business System -> Markdown Contracts -> Generic AZM Parser -> UniversalAzmIngester -> AZM Database`) is fully operational.

### 2. Idempotency Defect Fixed
- **Immutable Upgrades:** `ingestion_utils.py` was patched to use robust, database-agnostic `SELECT ... UPDATE` logic for idempotent upserts.
- **Regression Tested:** The test suite (`test_ingestion_idempotency.py`) verifies that repeated identical ingestions correctly skip (returning `SKIPPED`), and contract revisions successfully update properties and increment knowledge hashes in place, avoiding duplicates or unique constraint violations on `semantic_key`.

### 3. Complete ShopDeck Physical Schema Coverage
- **Source Views Governed:** The previous coverage gap (5 out of 13 views) has been resolved. All 13 authoritative public read views defined in `business_systems/shopdeck/public_read_views.sql` are now fully governed within `shopdeck-schematic-public-contract.md`.
- **Views Covered:**
  1. `vw_shopdeck_order_summary`
  2. `vw_shopdeck_order_line_items`
  3. `vw_shopdeck_customer_info`
  4. `vw_shopdeck_cancel_reason_events`
  5. `vw_shopdeck_checkout_external_events`
  6. `vw_shopdeck_checkout_input_error_events`
  7. `vw_shopdeck_order_cancellation_events`
  8. `vw_shopdeck_payment_gateway_events`
  9. `vw_shopdeck_rating_review_feedback_submit_events`
  10. `vw_shopdeck_return_exchange_events`
  11. `vw_shopdeck_post_order_survey_submit_events`
  12. `vw_shopdeck_shipment_ndr_reports`
  13. `vw_shopdeck_ndr_action_log`

### 4. Semantic → Schematic Resolution Confirmed
- Automated tests (`test_semantic_resolution.py`) prove that AZM natively resolves abstract intent to physical fields without domain hardcoding.
- **NDR Resolution:** `shopdeck.event.delivery_exception.reason` -> `vw_shopdeck_shipment_ndr_reports.latest_ndr_reason`
- **Accounting Resolution:** `shopdeck.entity.order.gross_value` -> `vw_shopdeck_order_summary.total_amount`
- **Customer Query:** `shopdeck.entity.customer` -> Maps to multiple distinct views dynamically.
- **Inventory Resolution:** `shopdeck.entity.order_quantity` -> `vw_shopdeck_order_line_items.quantity`

### 5. Multi-ID Neutrality & External Mapping Checked
- The namespace classifications remain distinct and accurate. Catalog is classified as `AARAM_NATIVE`, and ShopDeck as `EXTERNAL_CHANNEL`.
- External identifier mappings (e.g., `shopdeck.entity.order_item.customer_sku_short_id` mapping back to `catalog.entity.sku`) are validated properly.

### 6. NDR-ID Boundary Leakage Identified
During the repository audit, we identified legacy hardcoded knowledge in the NDR Intelligence Domain that requires refactoring in the next phase.
- **NDR-ID KNOWLEDGE LEAKAGE — REFACTOR REQUIRED:**
  - `src/azm/namespaces/ndr.py` defines hardcoded `NDR_CONCEPTS` and physical SQL schema inside `NDR_PUBLIC_VIEWS`.
  - `src/intelligence_domains/ndr/orchestrator.py` contains explicit `schemas` fallback mappings to `vw_shopdeck_shipment_ndr_reports`.
- Per the user directive, these definitions were **left intact** so as not to preempt the upcoming NDR-ID refactoring task, but their obsolete counterpart (the `shopdeck` fallback module) was completely removed from the AZM bootstrap sequence.

## Conclusion
The Universal Ingestion mechanism is fully compliant with the architectural vision. Brain Core can now rely entirely on the generic AZM repository to connect intent (semantic) with substrate (schematic) uniformly across all Business Systems.
