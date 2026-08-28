# Inventory Intelligence Domain Semantic Knowledge Source

**Status**: READ-ONLY DISCOVERY & CERTIFICATION
**Target Consumer**: Brain Core (Inventory Intelligence Domain / ID-2)

This document is the **SOURCE OF TRUTH** established by AaramInventory. It strictly defines the operational semantics that the Inventory Intelligence Domain (ID-2) is permitted to consume and represent in Azm.

---

## I. CERTIFIED CAPABILITIES

### 1. Stock Balance Capability
1. **Capability URN**: `urn:aarambooks:inventory:capability:balance`
2. **Exact business meaning**: Provides the real-time stock availability, allocations, and confidence score for a specific SKU in a specific warehouse.
3. **Authoritative source/model**: `InventoryBalanceModel` / `BalanceCalculatorService`
4. **Required constraints**: 
   - `inventory.entity.sku` (EQUALS)
   - `inventory.entity.warehouse` (EQUALS)
5. **Optional constraints**: None
6. **Accepted constraint types/formats**: UUID strings
7. **Response structure/semantics**: Returns `total_quantity`, `on_hand_quantity`, `allocated_quantity`, `in_transit_quantity`, and a `confidence_score` (0-100).
8. **Important domain terminology/synonyms**: "Stock", "Availability", "On hand", "Balance", "Allocated"
9. **Legitimate natural-language questions**: 
   - "How much stock do we have of SKU X in Warehouse Y?"
   - "How much of SKU X is allocated in Warehouse Y?"
10. **What it CANNOT answer**: 
    - "Is stock low?" (No certified low-stock thresholds).
    - "What is the valuation of this stock?"
11. **Certified business rules/policies**: Balances are unique per SKU+Warehouse. The system explicitly assigns a confidence score to balance records.
12. **Concepts in DB but not in CEM**: Reorder points or minimum stock levels (do not exist).
13. **Ambiguous semantics**: The exact business definition of "allocated" (e.g., hard reservation vs soft reservation) is handled by upstream systems.

### 2. Movement Ledger Capability
1. **Capability URN**: `urn:aarambooks:inventory:capability:ledger`
2. **Exact business meaning**: Provides a chronologically ordered history of atomic stock movements in and out of the system, along with a running balance.
3. **Authoritative source/model**: `InventoryMovementModel` / `InventoryLedgerService`
4. **Required constraints**: 
   - `inventory.entity.sku` (EQUALS)
5. **Optional constraints**: 
   - `inventory.temporal.posting_date` (GREATER_THAN, GREATER_THAN_EQUALS, LESS_THAN, LESS_THAN_EQUALS)
6. **Accepted constraint types/formats**: UUID strings (sku), ISO8601 Date strings (posting_date).
7. **Response structure/semantics**: Ordered list containing `movement_number`, `movement_type`, `quantity` (+/-), `posting_date`, and `running_balance`.
8. **Important domain terminology/synonyms**: "History", "Ledger", "Movements", "Transactions", "In/Out"
9. **Legitimate natural-language questions**: 
   - "Show me the movement history for SKU X."
   - "What movements happened for SKU X after January 1st?"
10. **What it CANNOT answer**: 
    - "What is the current LIFO/FIFO value of this ledger?" (Valuation is uncertified).
11. **Certified business rules/policies**: Movements differentiate strictly between `movement_date` (actual occurrence) and `posting_date` (system entry). 
12. **Concepts in DB but not in CEM**: `unit_cost` is stored in the DB but is not currently exposed or aggregated by the ledger capability.
13. **Ambiguous semantics**: Aging logic or "slow-moving" categorizations are strictly uncertified.

### 3. Job Work Custody Capability
1. **Capability URN**: `urn:aarambooks:inventory:capability:jobwork_status`
2. **Exact business meaning**: Aggregates and reports the custody of goods (raw materials and finished goods) held by an external job worker/vendor.
3. **Authoritative source/model**: `JobWorkerInventoryModel` / `JobWorkService`
4. **Required constraints**: 
   - `inventory.entity.jobwork_vendor` (EQUALS)
5. **Optional constraints**: 
   - `inventory.entity.sku` (EQUALS)
6. **Accepted constraint types/formats**: UUID strings.
7. **Response structure/semantics**: Returns a custody ledger showing `issued_quantity`, `consumed_quantity`, `returned_quantity`, and `pending_quantity`.
8. **Important domain terminology/synonyms**: "Job worker stock", "Vendor custody", "Pending materials", "Issued"
9. **Legitimate natural-language questions**: 
   - "How much stock is currently sitting with vendor X?"
   - "How much of SKU Y is pending with job worker X?"
10. **What it CANNOT answer**: 
    - "What is the scrap rate or wastage for this vendor?" (CEM does not expose scrap analysis).
11. **Certified business rules/policies**: Job work strictly tracks the lifecycle of Issued -> Consumed/Returned -> Pending.
12. **Concepts in DB but not in CEM**: `scrap_quantity` exists on Receipts, and `InventoryTransformationRecord` tracks BOM conversions, but these are not independently exposed via CEM.
13. **Ambiguous semantics**: SLA tracking, vendor performance, or "overdue" returns are uncertified.

### 4. Exception Status Capability
1. **Capability URN**: `urn:aarambooks:inventory:capability:exception_status`
2. **Exact business meaning**: Exposes formal discrepancies (mismatches between expected vs actual stock) detected across Physical, Marketplace, or Accounting boundaries.
3. **Authoritative source/model**: `InventoryExceptionModel` / `InventoryExceptionService`
4. **Required constraints**: 
   - `inventory.entity.sku` (EQUALS)
5. **Optional constraints**: 
   - `inventory.temporal.exception_date` (GREATER_THAN, GREATER_THAN_EQUALS)
6. **Accepted constraint types/formats**: UUID strings (sku), ISO8601 Date strings (exception_date).
7. **Response structure/semantics**: List of open exceptions with `expected_quantity`, `actual_quantity`, `difference`, `source_system`, and `status`.
8. **Important domain terminology/synonyms**: "Discrepancies", "Mismatches", "Missing stock", "Exceptions", "Count errors"
9. **Legitimate natural-language questions**: 
   - "Are there any physical count mismatches for SKU X?"
   - "Show me open exceptions for SKU Y."
10. **What it CANNOT answer**: 
    - "Which discrepancies are severe?" (No severity rules).
11. **Certified business rules/policies**: Exceptions are governed by a strict state machine (`OPEN`, `INVESTIGATING`, `RESOLVED`).
12. **Concepts in DB but not in CEM**: The `resolution_notes` field exists but is not strictly queried via CEM.
13. **Ambiguous semantics**: "Severity" or "Criticality" of an exception is NOT defined in AaramInventory and must not be assumed.

---

## II. CERTIFICATION MATRICES

### A. CERTIFIED VOCABULARY
The Intelligence Domain may safely seed the following terms into Azm:
- **Balance / Availability**: Quantity on hand, allocated quantity.
- **Ledger / Movement**: Historical in/out transactions.
- **Job Work Custody**: Pending, Issued, Consumed, Returned quantities held by vendors.
- **Exceptions / Discrepancies**: Expected vs Actual count mismatches.
- **Confidence Score**: System-generated metric of stock data reliability.

### B. CERTIFIED CAPABILITY MAPPING
- "How much..." / "Do we have..." → `urn:aarambooks:inventory:capability:balance`
- "Show history..." / "Transactions for..." → `urn:aarambooks:inventory:capability:ledger`
- "What does vendor hold..." / "Pending with..." → `urn:aarambooks:inventory:capability:jobwork_status`
- "Missing stock..." / "Mismatches for..." → `urn:aarambooks:inventory:capability:exception_status`

### C. CERTIFIED POLICIES
- Balances require BOTH a SKU and a Warehouse to be definitively resolved.
- Ledger movements are immutable once posted.
- Exceptions must specify a source system (Accounting, Marketplace, Physical).

### D. UNSUPPORTED / INFERRED / AMBIGUOUS KNOWLEDGE
The Intelligence Domain MUST NOT seed or assume the following concepts:
- **Low Stock / Reorder points**: UNSUPPORTED. Do not invent thresholds.
- **Inventory Valuation**: UNSUPPORTED. Do not invent LIFO/FIFO calculations.
- **Scrap Analysis**: INFERRED. Database tracks scrap, but no CEM capability certifies scrap analysis.
- **Exception Severity**: UNSUPPORTED. The system does not classify discrepancies as "major" or "minor".
- **Aging / Slow-moving stock**: UNSUPPORTED. 

### E. ID-2 HANDOFF RULE
The Inventory Intelligence Domain (ID-2) is explicitly authorized to seed semantic routing graphs and entity extraction maps for the **CERTIFIED CAPABILITIES** and **CERTIFIED VOCABULARY** listed above. 

The ID-2 MUST NOT invent business rules, valuation logic, alerting thresholds, or semantic capabilities that do not map 1:1 with an existing AaramInventory CEM capability. If a user asks a question falling into the "UNSUPPORTED" category, the ID-2 must route to a generic capability or explicitly state that the system does not support the request.
