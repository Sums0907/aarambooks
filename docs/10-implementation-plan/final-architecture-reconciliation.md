# Final Architecture Reconciliation

## Reconciliation of Proposed Owner Decisions

1. **ShopDeck should be the PRIMARY operational Context Provider:** VERIFIED. (ShopDeck MCP schemas prove it captures full checkout, order, delivery, and RTO lifecycle).
2. **AaramInventory provides only authoritative `quantity_on_hand` (no SKU details):** VERIFIED. (ShopDeck's `order_line_items` holds `product_name`, `product_color`, `product_size`).
3. **Brain may derive logical availability from `quantity_on_hand`:** VERIFIED.
4. **Brain should IGNORE AaramInventory `confidence_score`:** SUPPORTED. (Owner directive supersedes the payload structure).
5. **ShopDeck provides SKU identity/attributes:** VERIFIED.
6. **AaramInventory only for inventory quantity:** VERIFIED.
7. **AaramPacking should NOT be a Brain Context Provider:** VERIFIED. (It is an execution system. ShopDeck aggregates its outputs).
8. **Brain should not reconstruct context from AaramPacking:** VERIFIED.
9. **AaramPacking may remain an Action Engine target:** VERIFIED.
10. **Brain must NEVER own operational truth:** VERIFIED.
11. **Brain semantic models represent needs, NOT mirror payloads:** VERIFIED. (This resolves the perceived "schema mismatch" discrepancy).
12. **Do not invent authentication mechanisms:** VERIFIED.

---

## A. FINAL SOURCE-OF-TRUTH MATRIX

| Information | Source of Truth | Evidence | Brain Consumes? | Brain Owns? | Notes |
|---|---|---|---|---|---|
| Order | ShopDeck | `order_summary`, `order_line_items` | Yes | No | Base order data |
| Customer | ShopDeck | `customer_info`, tracking events | Yes | No | Identity, encrypted phone |
| SKU | ShopDeck | `sku_id`, `product_size` in line items | Yes | No | Catalog details provided by ShopDeck |
| Product attributes | ShopDeck | `product_color`, `product_name` | Yes | No | Provided directly in ShopDeck events |
| Shipment | ShopDeck | `order_line_items` | Yes | No | |
| AWB | ShopDeck | `awb_no` | Yes | No | |
| Courier | ShopDeck | `inhouse_courier_name`, `courier_allocation_type` | Yes | No | |
| Delivery status | ShopDeck | `seller_last_status`, `delivery_time` | Yes | No | |
| RTO/Return | ShopDeck | `rto_initiated`, `rto_delivered_at` | Yes | No | |
| Packing execution | AaramPacking | `PACKER_INVENTORY_INTEGRATION_README.md` | No | No | Brain only triggers actions here |
| Inventory quantity | AaramInventory | `/api/v1/read/inventory/balance` API | Yes | No | `quantity_on_hand` |
| Inventory confidence score | AaramInventory | `InventoryBalanceModel` | No | No | Brain explicitly ignores this |

---

## B. FINAL SYSTEM RESPONSIBILITY MATRIX

**ShopDeck:**
- **Owns:** Canonical Customer Order state, Payment state, shipment/courier tracking aggregation, and historical customer browsing/event telemetry.
- **Does NOT own:** Physical warehouse execution, actual warehouse inventory locations, physical inventory quantity ledger.

**AaramInventory:**
- **Owns:** Physical inventory truth, `quantity_on_hand` calculations, double-entry physical movements, physical SKU master catalogue definition.
- **Does NOT own:** E-commerce sales data, canonical customer identity, payment information, packing execution.

**AaramPacking:**
- **Owns:** Warehouse physical packing workflows, box scanning, label printing, physical RTO receiving validation.
- **Does NOT own:** Canonical order tracking (it just sends updates to ShopDeck), inventory ledgers, or customer context.

**Brain Core:**
- **Owns:** Semantic intelligence models, reasoning contexts, rule processing, and orchestrated decision generation.
- **Does NOT own:** Operational data, customer truth, inventory truth, or business state.

**Action Engine:**
- **Owns:** Formatting and dispatching Brain Core's decisions into concrete API requests to target execution systems.
- **Does NOT own:** Execution processing, operational context.

---

## C. PHASE 1 MODEL IMPACT

**NO CHANGES ARE REQUIRED TO PHASE 1 MODELS.**

- **InventoryContext:** Current field `items_availability: Dict[str, bool]` is sufficient because Brain derives boolean availability from AaramInventory's `quantity_on_hand`. `confidence_score` is explicitly ignored.
- **FulfillmentContext:** Current field `fulfillment_status: str` is sufficient because Brain semantic models only require the high-level status needed for reasoning, not the granular timestamp/tracking mirror of ShopDeck.
- **Reason:** Semantic abstraction. Brain maps complex physical reality into its own simplified semantic models.
- **Authoritative Source:** Owner directive #11 ("Brain semantic models must represent what Brain needs, NOT mirror the complete payloads").

---

## D. AUTHENTICATION BLOCKER

- **Verified Capability:** AaramIdentity currently supports OAuth2 Bearer JWT validation for human users via RSA public-key distribution (`decode_aaramidentity_token`).
- **Missing Capability:** Machine-to-Machine (M2M) authentication. Service accounts do not exist. Webhooks are currently network-trusted (Phase 1 legacy), but Brain Core API requests require a valid IdentityContext.
- **Required Owner Decision:** How should Brain Core technically authenticate its headless `GET` requests to AaramInventory and ShopDeck without impersonating a human? 
- **Must NOT be Invented:** Faked user credentials, bypassed endpoints, or fabricated tokens.

---

## E. AARAMPACKING DECISION

AaramPacking must be **COMPLETELY REMOVED** from the Brain Context boundaries.
- **Context Provider:** No.
- **Action Target:** Yes. (It remains an execution system for packing/RTO actions).
- **Operational System:** Yes.
- **Source of Truth:** No. (It pushes its execution state to ShopDeck).

---

## F. ADR-005 REVIEW

- **What is correct:** Promoting ShopDeck to Primary Context Provider. Deprecating AaramPacking as a Context Provider. Identifying the Authentication Blocker.
- **What is unsupported/needs correction:** The ADR proposed "Evolve Phase 1 Context Models: Modify the frozen Phase 1 Context Models... to explicitly map the exhaustive ShopDeck properties". This is **CONTRADICTED** by Owner Directive #11. Phase 1 models are semantic and should NOT mirror external payloads.
- **Ready for approval:** **NO**. ADR-005 must be amended to remove the requirement to modify Phase 1 schemas.

---

## G. ROADMAP IMPACT

After owner approval, `docs/10-implementation-plan/implementation-backlog.md` must change as follows:
1. **Phase 4:** Remove `AaramPacking` integration. Shift `ShopDeck` from Phase 5 to Phase 4 as the primary internal context provider. 
2. **Phase 5:** Remove `ShopDeck`. Retain external logistics/courier tracking only.
3. No changes to Phase 1 steps or deliverables.

---

## H. FINAL OWNER DECISIONS REQUIRED

1. **Authentication:** How will Brain Core authenticate its headless M2M requests to ShopDeck and AaramInventory given Identity Service Accounts are not yet built?

---

## I. NEXT STEP

**Wait for Owner to provide the Machine-to-Machine authentication architectural decision.**
