# ShopDeck Semantic Evidence Audit

**Status**: AUDIT ONLY - ARCHITECTURAL VETTING PASS
**Target System**: ShopDeck Business System
**Date**: September 2026

## 1. Executive Summary
This document provides a strictly evidenced audit of ShopDeck's operational schemas based on `internal_tables.sql` and `public_read_views.sql`. It evaluates the fields, statuses, relationships, and cross-system mappings. 

**Core Ownership Rule Enforced:**
- **ShopDeck BS:** Source Authority (authors/publishes meaning).
- **AZM:** Persistence/Federation Authority (ingests/persists/federates meaning).
- **Brain Core:** Orchestration Authority.
- **NDR-ID:** Intelligence Authority. 

---

## 2. Field Semantic Evidence Matrix

### CUSTOMER
| Field | View/Table | Entity | Business Meaning | Data Type | Authority | Evidence Source | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `customer_id` | `customer_info`, `order_line_items` | Customer | The internal ShopDeck identifier for the buyer. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | |
| `customer_number` | `customer_info` | Customer | The encrypted phone number of the customer. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | Proxied decryption on SELECT. |
| `customer_name` | `order_line_items`, `shipment_ndr_reports` | Customer | Customer's full name. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | |
| `drop_city`, `drop_state`, `drop_pincode` | `customer_info` | Address | The destination address components. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | Street address missing from views. |

### ORDER
| Field | View/Table | Entity | Business Meaning | Data Type | Authority | Evidence Source | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `order_id` | `order_summary`, `order_line_items` | Order | The primary identifier for a ShopDeck order. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | |
| `payment_mode` | `order_summary`, `order_line_items`, `shipment_ndr_reports` | Order | How the order was paid. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | |
| `payment_status` | `order_summary` | Order | State of the payment. | BOOLEAN | ShopDeck | `internal_tables.sql` | UNRESOLVED | **CONFLICT:** Boolean here, but Text in `order_line_items`. |
| `total_amount` | `order_summary` | Order | Gross order value. | NUMERIC | ShopDeck | `internal_tables.sql` | HIGH | |

### ORDER ITEM (LINE ITEMS)
| Field | View/Table | Entity | Business Meaning | Data Type | Authority | Evidence Source | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `sku_id` | `order_line_items` | OrderItem | The operational SKU string. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | |
| `quantity` | `order_line_items` | OrderItem | Number of units purchased in this order line. | INTEGER | ShopDeck | `internal_tables.sql` | HIGH | |
| `selling_price` | `order_line_items` | OrderItem | Final unit price. | NUMERIC | ShopDeck | `internal_tables.sql` | HIGH | |
| `customer_sku_short_id` | `order_line_items` | OrderItem | The external channel representation of the SKU. | TEXT | ShopDeck | `internal_tables.sql` | HIGH | Maps to Catalog BS. |
| `payment_status` | `order_line_items` | OrderItem | State of the payment at item level. | TEXT | ShopDeck | `internal_tables.sql` | UNRESOLVED | **CONFLICT:** Text here, but Boolean in `order_summary`. Semantic equivalence unproven. |

### SHIPMENT & NDR
| Field | View/Table | Entity | Business Meaning | Data Type | Authority | Evidence Source | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `awb_no` | `shipment_ndr_reports`, `ndr_action_log`, `customer_info` | Shipment | Air Waybill number, primary tracking ID. | TEXT | External Carrier (Exposed via ShopDeck) | `internal_tables.sql` | HIGH | |
| `courier_partner` | `shipment_ndr_reports` | Shipment | The logistics carrier name. | TEXT | External Carrier (Exposed via ShopDeck) | `internal_tables.sql` | HIGH | |
| `order_status` | `shipment_ndr_reports` | Shipment | The shipment state. | TEXT | External Carrier (Exposed via ShopDeck) | `internal_tables.sql` | HIGH | Exact ENUMs unproven. |
| `latest_ndr_reason` | `shipment_ndr_reports` | NDR | Raw string provided by the courier. | TEXT | External Carrier (Exposed via ShopDeck) | `internal_tables.sql` | HIGH | Semantics owned by Carrier. |
| `ndr_count` | `shipment_ndr_reports`, `ndr_action_log` | NDR | The number of failed attempts observed. | INTEGER | External Carrier (Exposed via ShopDeck) | `internal_tables.sql` | HIGH | |
| `action_type` | `ndr_action_log` | NDROutreach | Action taken by ShopDeck systems (SMS/IVR). | TEXT | ShopDeck | `internal_tables.sql` | HIGH | |

---

## 3. Status and Reason Semantics

ShopDeck SQL schema does not enforce ENUM constraints. The following statuses are categorized by evidence level.

### OBSERVED BUT SEMANTICALLY UNPROVEN VALUES
*(These values were previously inferred from NDR-ID logic, but lack authoritative ShopDeck business rules to prove them in isolation).*

| Field | Source Value | Inferred Meaning | Evidence Level |
|---|---|---|---|
| `order_status` | `DELIVERED`, `COMPLETE` | Successful delivery. | UNPROVEN (Inferred by NDR-ID) |
| `order_status` | `RTO_INITIATED`, `RETURNED` | Returned to origin. | UNPROVEN (Inferred by NDR-ID) |

### KNOWN STATUS VALUES
*None proven from SQL evidence alone. Formal ShopDeck documentation is required to establish the explicit ENUMs.*

---

## 4. Relationship Matrix

The authoritative physical keys linking entities:

- **Customer → Order:** Proven. `customer_info.customer_id` maps to `order_line_items.customer_id`.
- **Order → OrderItem:** Proven. `order_summary.order_id` maps to `order_line_items.order_id`. Cardinality: 1 to Many.
- **OrderItem → Shipment:** Proven. `order_line_items.awb_no` maps to `shipment_ndr_reports.awb_no`. Cardinality: Many OrderItems to 1 Shipment AWB.
- **Shipment → NDR Report:** Proven. `shipment_ndr_reports.awb_no`. Cardinality: 1 to 1 (Report is aggregated).
- **NDR Report → NDR Action Log:** Proven. `ndr_action_log.awb_no`. Cardinality: 1 to Many (Chronological log).

---

## 5. Cross-System Semantic Mappings

| ShopDeck Concept | AaramBooks Concept | Classification | Justification |
|---|---|---|---|
| `customer_sku_short_id` | `catalog.entity.sku` | **PROVEN** | Catalog contract explicitly defines this as the `CHANNEL_MAPPING`. |
| `quantity` (order_line_items) | `inventory.entity.demand` | **NOT EQUIVALENT** | `quantity` is commercial order size. `demand` is aggregate intent. Physical inventory is `manufactured_qty`. This mapping is invalid. |
| `awb_no` | `logistics.entity.shipment` | **PROBABLE** | AWB is a universal logistics concept, but exact Aaram logistics native contract mapping is not yet formally verified. |
| `product_id` | `catalog.entity.product` | **NOT EQUIVALENT** | Catalog contract explicitly states ShopDeck `product_id` is obsolete/null. |

---

## 6. Semantic Ownership and Evidence Classification

| Concept / Field | Source Authority | Semantic Status | Consumer | Owner |
|---|---|---|---|---|
| `customer_sku_short_id` | ShopDeck | PROVEN | AZM / Brain | ShopDeck BS defines it; AZM maps it to Catalog. |
| `latest_ndr_reason` | External Carrier | PROVEN | Brain / NDR-ID | Carrier defines raw text. NDR-ID interprets it. ShopDeck just stores/exposes it. |
| `payment_status` (Conflict) | ShopDeck | UNKNOWN | Brain / Accounting | ShopDeck BS must resolve the boolean/text conflict. |

---

## 7. Contract Readiness Gate

### READY TO AUTHOR
- **Semantic Contract:** **YES** (with Provisional gaps for unproven ENUMs).
- **Schematic Contract:** **YES** (13 views are strictly defined).

### BLOCKING ISSUES
- None preventing authorship, provided the unresolved items are explicitly marked as provisional.

### SAFE PROVISIONAL ITEMS
- `payment_status` definition (Boolean vs Text mismatch).
- Exact ENUM values for `order_status` and `ndr_status` (Must be documented as provisional until ShopDeck source code/API rules confirm them).

### MUST NOT ENTER SHOPDECK CONTRACT
*The following are intelligence-domain decisions or orchestrations that must remain strictly outside the ShopDeck Business System contracts:*

- **NDR-ID Intelligence (Do Not Include):**
  - "Door locked" maps to `CUSTOMER_UNAVAILABLE`.
  - Fake-attempt or buyer-remorse diagnoses.
  - Priority, operational risk, or CX risk scoring.
  - 3 attempts = Priority Concierge Escalation (ShopDeck only tracks `ndr_count`).
  - RTO avoidance prediction or reschedule strategies.
  - Freight savings calculation.
- **Brain Core Logic (Do Not Include):**
  - Execution flows or API routing logic.
