# R-7 Document Identifier & Reference Ownership Audit

## 1. Executive Conclusion
The forensic audit reveals a split ownership model across the AaramBooks Inventory system:
- **Domain-generated**: Job Work identifiers (`issue_reference`, `return_number`) are cleanly generated inside the authoritative domain service (`JobWorkService`) using database sequence models.
- **Application/API-generated**: Stock Adjustment movement identifiers (`movement_number`) and manual references are constructed in the FastAPI router layer (`movement_router.py`) before passing them to the domain service.
- **Caller-supplied business input**: Goods Receipt (`grn_number`), Purchase Return (`return_number`), and Transformation (`reference_document`) are strictly required by the domain schemas and are currently passed down directly from the API layer without generation, indicating they are treated as external business inputs provided by the user/frontend.

## 2. Goods Receipt
- **Generation/supply path**: `GoodsReceiptService.create` strictly requires `grn_number` via the `GoodsReceiptCreate` Pydantic schema. It performs a uniqueness check against the repository but **does not generate** the number. 
- **Existing callers**: The API route (`POST /goods-receipts`) takes `GoodsReceiptCreate` directly as a request payload, meaning the frontend/caller supplies the `grn_number`. Automated test scripts (e.g., `certify_bom_module.py`) hardcode values like `"GRN-JW-01"`.
- **Conclusion**: `grn_number` is currently a caller-supplied business input.

## 3. Purchase Return
- **Generation/supply path**: `PurchaseReturnService.create` requires `return_number` via the `PurchaseReturnCreate` schema. Like Goods Receipt, it enforces uniqueness but does not generate the sequence.
- **Existing callers**: The API route (`POST /purchase-returns`) takes `PurchaseReturnCreate` directly. 
- **Conclusion**: `return_number` is currently a caller-supplied business input.

## 4. Transformation
- **Meaning and source**: `InventoryTransformationEngine.execute_transformation` consumes a `TransformationRequest` which requires a `reference_document`. This document string is then used by the engine to generate an internal movement number (`f"MOV-CONS-{request.reference_document}-{uuid.uuid4().hex[:6]}"`) and is saved immutably to the `InventoryTransformationRecord`.
- **Conclusion**: `reference_document` is a required business input linking the physical transformation to an external trigger (like a GRN or production order).

## 5. Stock Adjustment
- **movement_number**: The `InventoryMovementService.create_movement` requires `movement_number` via `InventoryMovementCreate`, but **does not generate it**. Instead, the FastAPI routers (`movement_router.py`) generate UUID-based identifiers like `f"MOV-ADJ-{uuid.uuid4().hex[:8].upper()}"` before calling the service.
- **reference_type**: Hardcoded at the API router level based on the specific endpoint (e.g., `"MANUAL"` for manual adjustments, `"STOCK_COUNT"` for physical counts).
- **reference_id**: For manual adjustments, the API router explicitly uses a null UUID (`00000000-0000-0000-0000-000000000000`). It does **not** use the warehouse_id as the reference_id.
- **Conclusion**: Stock adjustments identifiers are Application/API-generated.

## 6. Existing Job Work Pattern
`JobWorkService` establishes a fundamentally different architectural pattern. When `issue_material` or `return_material` is called, the service internalizes the generation:
```python
seq_name = f"JW-ISS-{today.strftime('%d%m%y')}"
seq_val = await get_next_sequence_value(session, seq_name)
issue_reference = f"{seq_name}-{seq_val:03d}"
```
This proves that transaction-safe, domain-owned sequence generation is a proven pattern in this codebase. However, this pattern has not been applied to Goods Receipt or Purchase Return.

## 7. Existing Callers
- **FastAPI Routes**: Pass schemas directly from the request body (Goods Receipt, Purchase Return). Generate UUIDs for movements internally (`movement_router.py`).
- **Test Scripts**: Hardcode sequence numbers (`"TEST-MOV-123"`, `"GRN-01"`).

## 8. R-7 Architectural Consequence

1. **Goods Receipt**: REQUIRES DOMAIN-SERVICE CHANGE (or user input). Since R-7 cannot invent business inputs, either the user must provide the GRN number via Brain Core, or the domain must adopt the Job Work pattern and generate it internally.
2. **Purchase Return**: REQUIRES DOMAIN-SERVICE CHANGE. Same as above.
3. **Transformation**: REQUIRES USER/BUSINESS INPUT. `reference_document` is a semantic link to an external event, not a sequence. Brain Core must extract it.
4. **Stock Adjustment**: READY AFTER EXISTING GENERATOR IS REUSED. R-7 acts as an API integration layer; it can safely replicate the `uuid4` generation and null UUID reference logic already established by the `movement_router.py` API layer.

## 9. Recommendation
Do not force R-7 to invent document numbers. For Goods Receipt and Purchase Return, apply the existing `JobWorkService` sequence generation pattern (using `get_next_sequence_value`) directly into `GoodsReceiptService` and `PurchaseReturnService`. Make the schema fields `Optional[str]` so callers *can* supply them (preserving existing API behavior) but the domain will auto-generate them if missing (allowing R-7 to safely execute).

## 10. R-7 Decision Gate
- **Decisions requiring user approval**: Modifying `GoodsReceiptService` and `PurchaseReturnService` to auto-generate sequence numbers when omitted by the caller.
- **Decisions already established**: Stock adjustment movement numbers and null UUID references are safely generated by the API/integration layer (`movement_router.py`). R-7 can adopt this safely.
- **Exact next implementation step**: Modify `GoodsReceiptService` and `PurchaseReturnService` to conditionally generate document identifiers using `SequenceModel`, then update their Pydantic schemas to make the fields optional.
