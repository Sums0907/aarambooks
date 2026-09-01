# R-7 Inventory Adapter Implementation Plan

## Goal Description
Implement the R-7 Payload Construction Adapters for the seven authoritative action capabilities in the `Aaram_Inventory` workspace (`src/domains/context/capabilities/r7_action_capabilities.py`).

These adapters will consume the R-5 resolved `business_id`s (UUIDs) and the strictly-typed `NormalizedParameter`s passed from Brain Core, validating and mapping them to authoritative Inventory domain schemas (e.g., `GoodsReceiptCreate`).

## Proposed Changes

### Phase 1: Payload Construction Logic
For each of the 7 capabilities inside `r7_action_capabilities.py`, I will implement the `execute` method to:
1. Extract the R-5 resolved UUIDs from `resolved_candidates`.
2. Extract the strictly-typed scalar values from `understanding.parameters` (matching names like `inventory.numeric.quantity`).
3. Validate that all required domain fields are present.
4. Construct the domain-specific Pydantic schema (e.g., `GoodsReceiptCreate`).
5. Invoke the injected domain service (e.g., `GoodsReceiptService.create_receipt()`).
6. Catch validation/domain exceptions and map them to `EXECUTION_LIMITATION`.

### Phase 2: Capability-by-Capability Mapping

1. **Goods Receipt**: Maps `inventory.entity.supplier`, `warehouse`, and `sku` (R-5) and `inventory.numeric.quantity`, `inventory.temporal.posting_date` (Scalars) to `GoodsReceiptCreate`.
2. **Purchase Return**: Maps to `PurchaseReturnCreate` schema.
3. **Transformation**: Maps to `TransformationRequest` schema.
4. **Job Work Issue**: Maps to `JobWorkIssueCreate`.
5. **Job Work Return**: Maps to `JobWorkReturnCreate`.
6. **Exception Resolution**: Maps to `ExceptionResolution` model.
7. **Stock Adjustment**: Maps to `InventoryMovementCreate`.

> [!WARNING]
> If any capability has an unclear, incomplete, or incompatible schema (e.g., it strictly requires fields that cannot be naturally mapped from the semantic input and should not be invented, such as an external invoice number or a generated `grn_number` not handled by the domain service internally), I will STOP implementation for that specific capability and flag it as a blocker.

### Phase 3: Focused Testing
I will create a test suite in `/Users/sumatidhingra/Documents/AaramBooks/Aaram_Inventory/tests/domains/context/test_r7_action_adapters.py` (or equivalent location) that verifies:
- Valid payloads trigger domain services successfully.
- Missing required semantic parameters return `EXECUTION_LIMITATION` instead of throwing 500s.
- R-7 strictly avoids database mutation (mocking the domain services to prove boundary compliance).

## User Review Required

> [!IMPORTANT]
> **Domain Schema Constraints**: The `GoodsReceiptCreate` schema requires fields like `grn_number`. Since R-7 cannot "invent" missing values, if the user conversational intent doesn't provide a `grn_number`, should R-7 return an `EXECUTION_LIMITATION`, or does the Inventory domain have a standard practice for auto-generating these if omitted? 

## Open Questions
- Is `BypassSandbox: true` fully permitted for executing the testing and file modifications inside `/Users/sumatidhingra/Documents/AaramBooks/Aaram_Inventory/`?
- For capabilities with missing schemas (e.g., if `JobWorkReturnCreate` does not exist in the codebase), should I just leave it returning the current `{"status": "PENDING_IMPLEMENTATION", ...}`?

## Verification Plan
1. Run the focused R-7 adapter tests inside the `Aaram_Inventory` workspace.
2. Verify all R-7 capability classes are registered and executable.
3. Generate the `R-7-INVENTORY-ADAPTER-IMPLEMENTATION-REPORT.md` document detailing exact mappings, limitations, and the final certification status (Certified vs Blocked).
