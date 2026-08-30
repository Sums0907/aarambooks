# R-7 Deep Architectural Study

## 1. Executive Conclusion
R-7, as currently implemented, is an **execution-routing skeleton**. It correctly establishes the architectural boundaries, sets up the `R7ExecutionService` orchestrator, resolves entities via R-5, and provides an independent `/cem/v1/execute` endpoint. However, the concrete capability classes currently return `PENDING_IMPLEMENTATION` because the crucial **payload-construction boundary**—converting semantic `ConversationalUnderstanding` and resolved UUIDs into strict domain DTO schemas (like `GoodsReceiptCreate`)—is not yet built.

Therefore, R-7 is not architecturally complete; it is functionally routed but pending the critical capability adapter layer.

## 2. Authoritative ACTION Census

Based on the domain services in the Inventory CEM, the following is the complete authoritative inventory of business-state-changing operations that legitimately belong in RABTA/CEM:

| Capability Name | Intent | Authoritative Domain Service | Authoritative Method | Mutates State? | Tx Boundary |
| --- | --- | --- | --- | --- | --- |
| Goods Receipt | ACTION | `GoodsReceiptService` | `create()` | Yes | Explicit DB Tx (`session.commit/rollback`) |
| Purchase Return | ACTION | `PurchaseReturnService` | `create()` | Yes | Explicit DB Tx |
| Transformation | ACTION | `InventoryTransformationEngine` | `execute_transformation()` | Yes | Explicit DB Tx |
| Job Work Issue | ACTION | `JobWorkService` | `issue_materials()` | Yes | Explicit DB Tx |
| Job Work Return | ACTION | `JobWorkService` | `receive_materials()` | Yes | Explicit DB Tx |
| Exception Resolution | ACTION | `InventoryExceptionService` | `resolve_exception()` | Yes | Explicit DB Tx |
| Stock Adjustment | ACTION | `InventoryMovementService` | `create_movement()` | Yes | Explicit DB Tx |

**Missing/Excluded:**
- Internal database triggers or background cron jobs for ledger reconciliation must NOT become RABTA capabilities.

## 3. Seven Capability Execution Traces

1. **Goods Receipt**: `R7GoodsReceiptCapability` -> `GoodsReceiptService.create(schema: GoodsReceiptCreate)`. Touches `GoodsReceiptRepository` and `InventoryMovementService`. Protected by explicit `session.commit()` on success, `session.rollback()` on exception.
2. **Purchase Return**: `R7PurchaseReturnCapability` -> `PurchaseReturnService.create(schema: PurchaseReturnCreate)`. Creates return documents and negative movements. Transaction-safe.
3. **Transformation**: `R7TransformationCapability` -> `InventoryTransformationEngine.execute_transformation(request: TransformationRequest)`. Consumes BOM, creates stock out/in movements. Transaction-safe.
4. **Job Work Issue**: `R7JobWorkIssueCapability` -> `JobWorkService.issue_materials(schema: JobWorkIssueCreate)`. Creates issue document and transfer movements. Transaction-safe.
5. **Job Work Return**: `R7JobWorkReturnCapability` -> `JobWorkService.receive_materials(schema: JobWorkReturnCreate)`. Creates receipt document, generates transformations, handles scrap. Transaction-safe.
6. **Exception Resolution**: `R7ExceptionResolutionCapability` -> `InventoryExceptionService.resolve_exception(schema)`. Updates exception status and triggers reconciliation movements. Transaction-safe.
7. **Stock Adjustment**: `R7StockAdjustmentCapability` -> `InventoryMovementService.create_movement(schema: InventoryMovementCreate)`. Direct adjustment via a `STOCK_ADJUSTMENT` movement type. Transaction-safe.

*Calling any of these from R-7 preserves all existing business invariants because the domain services enforce them internally.*

## 4. Payload-Construction Boundary Analysis

**Where does semantic information become a domain-specific ACTION payload?**

Brain Core semantic request
        ↓
R-5 entity resolution
        ↓
**[ R-7 Capability Adapter ]** *(Payload Construction)*
        ↓
Domain service
        ↓
Mutation

**Decision: B. R-7 Capability Adapter.**
According to the ecosystem flow, Brain Core is schema-agnostic. Domain services expect strict Python DTOs (Pydantic schemas). Therefore, the CEM layer (specifically the R-7 concrete capability implementations like `R7GoodsReceiptCapability`) MUST bridge this gap. The R-7 capability is responsible for taking the `ConversationalUnderstanding` (which contains raw values like quantities) and `resolved_candidates` (the UUIDs from R-5) and mapping them into the `GoodsReceiptCreate` domain schema before invoking the domain service.

## 5. R-4 / R-5 / R-6 / R-7 Boundary Matrix

| Layer | Knows | May do | Must not do |
| --- | --- | --- | --- |
| **R-4 (Discovery)** | Capability Registry, Applicability rules | Check if a semantic intent applies to local capabilities | Mutate state, construct domain DTOs |
| **R-5 (Resolution)** | Semantic names, Aliases, Physical UUIDs | Translate strings to UUIDs, identify ambiguity | Decide conversational intent, execute actions |
| **R-6 (Refinement)** | Conversational history, Prompting | Ask user to clarify ambiguity | Bypass R-5, construct DTOs |
| **R-7 (Execution)** | Domain DTO schemas, Domain Services | Map UUIDs/semantics to DTOs, trigger domain mutation | Route non-ACTION intents, invent entity IDs |

## 6. ACTION API Contract Analysis

Based on `cem_router.py` and `RABTA-CEM-INTEGRATION-CONTRACT.md`:
- ACTION **does not** enter through `/cem/v1/discover`.
- There is a separate execution endpoint: `/cem/v1/execute` which exclusively accepts the `ACTION` intent.
- The contract requires the response to be a `BusinessEvidenceResponse`.
- R-7 is supposed to execute immediately if safe. If it succeeds, it returns `EVIDENCE_AVAILABLE` with `evidence_data`. If it fails validation or has missing parameters, it returns `EXECUTION_LIMITATION`.
- Brain Core receives this factual evidence and passes it up the chain.

## 7. Multiple Action Capability Matches

If an `ACTION` request matches multiple capabilities (e.g., both `GoodsReceipt` and `PurchaseReturn`), the correct architectural behavior is for `R7ExecutionService` to return `EXECUTION_LIMITATION` with `missing_parameter="capability"`. 
- **Exactly one must execute.** R-7 should **not** guess, and it should **not** execute both. It must return ambiguity, allowing Brain Core to trigger R-6 bounded refinement.

## 8. Failure and Safety Model

- **Missing Parameters**: R-7 capability checks `get_required_semantics()`. If missing, returns `EXECUTION_LIMITATION`.
- **Ambiguous Entities**: R-5 returns `AMBIGUOUS`. R-7 aborts execution and returns `MULTIPLE_CANDIDATES`.
- **Business-rule Rejection**: Domain service raises `ValidationException`. R-7 catches it and returns `EVIDENCE_UNAVAILABLE` or `EXECUTION_LIMITATION`.
- **Transaction Failure**: Handled internally by Domain Services via SQLAlchemy `session.rollback()`.
- **Partial Failure**: Impossible by design; all domain services enforce single-transaction boundaries. R-7 cannot leave the business in a partially mutated state.

## 9. R-5 Dependency Analysis

To successfully execute actions, the following R-5 resolvers must be confirmed/implemented:
- `inventory.entity.supplier`: Needs UUID for Job Worker/Supplier models.
- `inventory.entity.sku`: Needs UUID for SKU models.
- `inventory.entity.warehouse`: Needs UUID for Warehouse models.
- `inventory.entity.job_worker`: Alias/equivalent to supplier (JobWorker model).
- `inventory.entity.exception`: Needs UUID for Exception models.

## 10. Current Implementation Gap Matrix

| Capability | Routing exists | R-5 inputs exist | Payload construction | Domain execution | Tx safe | Fully executable? |
| --- | --- | --- | --- | --- | --- | --- |
| Goods Receipt | Yes | Partial | No | Yes | Yes | **No** |
| Purchase Return | Yes | Partial | No | Yes | Yes | **No** |
| Transformation | Yes | Partial | No | Yes | Yes | **No** |
| Job Work Issue | Yes | Partial | No | Yes | Yes | **No** |
| Job Work Return | Yes | Partial | No | Yes | Yes | **No** |
| Exception Res. | Yes | Partial | No | Yes | Yes | **No** |
| Stock Adjustment | Yes | Partial | No | Yes | Yes | **No** |

## 11. Definition of R-7 COMPLETE

**R-7 is defined as COMPLETE when:**
1. All registered R-7 ACTION capabilities contain working Payload Construction logic, successfully mapping `ConversationalUnderstanding` parameters (like dates/quantities) and R-5 resolved UUIDs into their respective domain Pydantic schemas (e.g., `GoodsReceiptCreate`).
2. All capabilities successfully invoke their authoritative domain services.
3. Database writes successfully commit and factual evidence is returned inside `BusinessEvidenceResponse.evidence_data`.
4. R-7 exhaustion tests pass using realistic schema payloads.

## 12. Recommended Next Step

**Implement the Payload Construction Adapters inside the R-7 Capabilities**, translating `ConversationalUnderstanding` components (such as scalar quantities) and R-5 UUIDs into the strict Domain Create DTOs.

## 13. Open Architectural Questions
- How are scalar non-entity parameters (e.g., numeric quantities, dates) identified in the semantic payload? Brain Core currently classifies entities, but does it reliably send `inventory.numeric.quantity` via `ConversationalComponent` for R-7 to populate schemas?
