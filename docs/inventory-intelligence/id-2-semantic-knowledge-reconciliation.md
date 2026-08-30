# ID-2 Semantic Knowledge Reconciliation

## 1. EXECUTIVE SUMMARY
The original ID-2 specification is **partially valid and requires significant revision**. Several core concepts and policies proposed in the original design (e.g., Low Stock, Reorder Thresholds, Jobwork Aging, and Valuation) are explicitly **UNSUPPORTED** or **INFERRED** by the authoritative AaramInventory specification. Brain Core and the Inventory ID must NOT invent business rules or parameters that the authoritative source system does not natively own or expose. The ID-2 semantic knowledge must be pared down to strictly match what the AaramInventory CEM provides.

## 2. CERTIFIED KNOWLEDGE
These concepts and capabilities are directly supported by AaramInventory and are cleared for Azm seeding:

### Core Concepts:
- **SKU:** (`inventory.entity.sku`) Exact UUID filter.
- **Warehouse:** (`inventory.entity.warehouse`) Exact UUID filter.
- **Jobworker / Vendor:** (`inventory.entity.jobwork_vendor`) Exact UUID filter for third-party custody.
- **Movement / Ledger Entry:** (`inventory.entity.posting_date`) Chronological ledger events.
- **Exception / Discrepancy:** Mismatches between expected and actual quantities (`inventory.temporal.exception_date`).
- **Pending Return:** Remaining raw materials awaiting finished goods receipt from a jobworker.

### Certified Policies:
- **Unique Stock Keeping:** Balances are unique per warehouse and SKU.
- **Movement Immutability:** Posted movements are immutable.
- **Exception Lifecycle:** Exceptions track states (OPEN, INVESTIGATING, RESOLVED).

## 3. INFERRED KNOWLEDGE
These concepts exist in the underlying system but are not independently certified as CEM semantics:
- **Scrap / Wastage:** Tracked during job work receipts in the DB (`scrap_quantity`), but no dedicated CEM capability exposes scrap analytics directly.
- **Valuation Strategy:** The movement ledger tracks `unit_cost`, allowing for FIFO/Average cost calculation, but a strict valuation strategy is not codified by the CEM.
- **Stock Allocations:** The balance capability returns `allocated_quantity`, but the exact reservation rules (hard vs soft) are undefined.

## 4. UNSUPPORTED KNOWLEDGE
These concepts from the old ID-2 proposal must **NOT** be seeded into Azm, as they are not established by AaramInventory:
- **Low Stock Definition:** AaramInventory does not define reorder points or low-stock thresholds.
- **Reorder Threshold Policy:** Do not invent a policy recommending reorders based on arbitrary days of trailing dispatch.
- **Valuation / COGS Policy:** Do not create a certified financial valuation semantic rule.

## 5. AMBIGUOUS KNOWLEDGE
These concepts require a future business decision from AaramInventory before they can be certified in Brain Core:
- **Negative Stock Severity:** Do not assume a "High Severity System Discrepancy" policy. The system tracks exceptions, but does not dictate business severity.
- **Jobwork Aging Policy:** Do not assume a ">30 days" aging rule for jobwork materials. Aging thresholds are not established.

## 6. FINAL SEMANTIC VOCABULARY
The authorized Inventory ID vocabulary to be seeded into Azm:
- **SKU**
- **Warehouse**
- **Jobworker / Vendor**
- **Movement**
- **Exception**
- **Pending Return**

## 7. FINAL CAPABILITY MAPPING

| Capability URN | Business Meaning | Source | Required Constraints | Optional Constraints | Response Semantics | Natural-Language Example |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `urn:aarambooks:inventory:capability:balance` | Current stock balance | `InventoryBalanceModel` | `sku`, `warehouse` | None | `total_quantity`, `on_hand_quantity`, `allocated_quantity`, `in_transit_quantity`, `confidence_score` | "What is the stock of SKU X in Warehouse Y?" |
| `urn:aarambooks:inventory:capability:ledger` | Historical stock movements | `InventoryMovementModel` | `sku`, `posting_date` | None | Atomic movements list and `running_balance` | "Show me the movement history of SKU X." |
| `urn:aarambooks:inventory:capability:jobwork_status` | Stock held by vendor | `JobWorkerInventoryModel` | `jobwork_vendor` | `sku` | Custody ledger aggregating issued, consumed, pending | "What is Vendor X holding?" |
| `urn:aarambooks:inventory:capability:exception_status` | Active discrepancies | `InventoryExceptionModel` | `sku` | `exception_date` | Expected vs actual quantities and source | "Are there discrepancies for SKU X?" |

## 8. POLICY CATALOG

### Certified Policies
- **Stock Tracking:** All balances require a valid SKU and Warehouse identity.
- **Job Work Accountability:** Job workers are accountable for the delta between issued and returned/consumed stock (Pending Return).
- **Immutable Movements:** Stock changes must be calculated by aggregating immutable ledger entries.

### Inferred Policies
- **Scrap Tracking:** Scrap exists as domain data tied to Job Work Receipts.

### Proposed / Future Policies (DO NOT IMPLEMENT)
- Reorder Threshold Policy
- Jobwork Aging Escalation
- Automated Valuation (COGS)
- Negative Stock Escalation

## 9. NATURAL LANGUAGE MAPPINGS

**Supported Mapping:**
- "What is the stock of SKU X?" → `urn:aarambooks:inventory:capability:balance`
- "Show me the movement history of SKU X." → `urn:aarambooks:inventory:capability:ledger`
- "What is Vendor X holding?" → `urn:aarambooks:inventory:capability:jobwork_status`
- "Are there discrepancies for SKU X?" → `urn:aarambooks:inventory:capability:exception_status`

**CANNOT BE ANSWERED (UNSUPPORTED):**
- "Which SKUs are low in stock?" (No low-stock threshold established)
- "What is the total value of our inventory?" (No formal valuation strategy established)
- "Which vendors have overdue materials >30 days?" (No aging policy established)

## 10. ID-2 AZM SEEDING RECOMMENDATION
ID-2 should seed the `AzmProvider` ONLY with the **Certified Knowledge** concepts and the **Final Capability Mapping**. The prompt logic in ID-2's orchestrator must gracefully decline to answer questions about low stock, valuation, or aging rules, explaining that those business policies are not defined in the system.

## 11. BOUNDARY VERIFICATION
- **AaramInventory** → Owns operational truth and defines the capabilities (e.g. `balance`, `ledger`).
- **Inventory ID** → Owns Inventory semantic interpretation (mapping "history" to `ledger`), but does NOT invent business rules.
- **Brain Core** → Owns generic reasoning/context infrastructure (the Gateway/Assembler).
- **CEM** → Exposes certified operational capabilities (e.g. `urn:aarambooks:inventory:capability:balance`).
- **Azm** → Stores/retrieves semantic knowledge used by the ID to perform the mapping.

## 12. IMPLEMENTATION READINESS
ID-2 is **READY**. 
The discrepancies from the old proposal have been cleanly mapped to UNSUPPORTED. The domain can now safely seed the certified concepts into Azm without violating the business logic boundary.
