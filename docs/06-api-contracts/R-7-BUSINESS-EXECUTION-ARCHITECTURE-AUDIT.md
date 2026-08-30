# R-7 BUSINESS EXECUTION ARCHITECTURE AUDIT

## 1. R-7 Responsibility and Boundary
R-7 Business Execution exclusively owns state-changing operations within the Context Execution Module (CEM).
It acts upon semantic requests that have already passed through R-4 (Business Discovery), been resolved by R-5 (Semantic Entity Resolution), and finalized by R-6 (Bounded Refinement). 
R-7 strictly avoids conversational parsing, discovery logic, or entity ambiguity resolution. Its sole responsibility is to orchestrate internal, transactional domain services using fully resolved physical inputs, enforce business/data invariants, and return factual execution evidence.

## 2. Complete Repository-Derived R-7 Capability Census
Based on a programmatic inspection of `src/domains/inventory/services` and API routes, the following capabilities have been classified:

### A. R-7 Business Execution Candidates
1. **Goods Receipt Creation**
2. **Purchase Return Creation**
3. **Inventory Transformation**
4. **Job Work Issue**
5. **Job Work Return**
6. **Exception Resolution**
7. **Inventory Adjustments (Stock Counts, RTO, Customer Returns, Manual)**

### B. Internal Implementation Operations (NOT CEM/RABTA)
- `OutboundEventDispatcherService.dispatch_pending_events` (Background Sync/Outbox)
- `BalanceCalculatorService.recalculate_balance` (Snapshot mechanism)
- Master Data Setup / Import Pipelines

### D. Covered Elsewhere
- `PackerIntegrationService.process_packer_event` (Direct application integration webhook, outside conversational boundaries).

## 3. Capability-by-Capability Implementation Mapping

### 1. Goods Receipt
- **Intent**: ACTION: Create Goods Receipt (PO or ASN fulfillment).
- **Service**: `GoodsReceiptService.create`
- **Semantic Inputs**: `inventory.entity.supplier`, `inventory.entity.sku`, `inventory.entity.warehouse`, `quantity`, `document_reference`.
- **Physical Identifiers**: Supplier UUID, SKU UUID, Warehouse UUID.
- **R-5 Dependency**: Resolving Supplier, SKU, Warehouse.
- **Transaction**: Safe. Mutations occur inside isolated DB transactions.

### 2. Purchase Return
- **Intent**: ACTION: Create Purchase Return (RTV).
- **Service**: `PurchaseReturnService.create`
- **Semantic Inputs**: `inventory.entity.supplier`, `inventory.entity.sku`, `inventory.entity.warehouse`, `quantity`, `document_reference`.
- **Physical Identifiers**: Supplier UUID, SKU UUID, Warehouse UUID.
- **R-5 Dependency**: Supplier, SKU, Warehouse.

### 3. Inventory Transformation
- **Intent**: ACTION: Convert BOM components into finished goods.
- **Service**: `InventoryTransformationEngine.execute_transformation`
- **Semantic Inputs**: `inventory.entity.sku` (Target), quantity, `inventory.entity.warehouse` or `inventory.entity.job_worker`.
- **Physical Identifiers**: Target SKU UUID, Location UUID (Warehouse/Job Worker).
- **R-5 Dependency**: Target SKU, Location entities.

### 4. Job Work Issue
- **Intent**: ACTION: Issue raw materials to Job Worker.
- **Service**: `JobWorkService.issue_material`
- **Semantic Inputs**: `inventory.entity.sku`, `inventory.entity.job_worker`, `quantity`.
- **Physical Identifiers**: SKU UUID, Supplier (Job Worker) UUID.
- **R-5 Dependency**: Job Worker, SKU.

### 5. Job Work Return
- **Intent**: ACTION: Return processed goods from Job Worker.
- **Service**: `JobWorkService.return_material`
- **Semantic Inputs**: `inventory.entity.sku`, `inventory.entity.job_worker`, `quantity`.
- **Physical Identifiers**: SKU UUID, Supplier UUID.
- **R-5 Dependency**: Job Worker, SKU.

### 6. Exception Resolution
- **Intent**: ACTION: Resolve an inventory exception via reconciliation.
- **Service**: `InventoryExceptionService.resolve_exception`
- **Semantic Inputs**: `inventory.entity.exception` (Exception ID), resolution notes.
- **Physical Identifiers**: Exception UUID.
- **R-5 Dependency**: The specific exception UUID. (Requires an R-5 resolver for `inventory.entity.exception`).

### 7. Inventory Adjustments
- **Intent**: ACTION: Direct movement adjustment.
- **Service**: `InventoryMovementService.create_movement`
- **Semantic Inputs**: `inventory.entity.sku`, `inventory.entity.warehouse`, `quantity`, `reason_code`.
- **Physical Identifiers**: SKU UUID, Warehouse UUID.
- **R-5 Dependency**: SKU, Warehouse.

## 4. R-7 vs R-4 Boundary
R-4 dictates *whether* execution is applicable. R-4 reads. R-7 executes.
R-7 will never perform an R-4 capability check mid-transaction; it trusts that Brain Core orchestrates R-4 applicability logic *before* triggering the R-7 intent. 

## 5. R-7 vs R-5 Boundary
R-7 operates strictly on opaque physical IDs (UUIDs). Any semantic entities provided in the `AbstractEvidenceRequest` mapping to the R-7 capability must be funneled through `SemanticResolverRegistry` (R-5). If R-5 returns `AMBIGUOUS`, R-7 immediately fails back to Brain Core for R-6 refinement. R-7 never implements custom text-matching.

## 6. R-7 vs R-6 Boundary
R-7 never initiates refinement conversations. If missing parameters exist, R-7 returns `EXECUTION_LIMITATION`. If entities are ambiguous, it returns the candidates. R-6 bounded refinement takes place completely outside R-7.

## 7. R-7 Transaction/Mutation Model
Execution in R-7 must map 1:1 with isolated Database `AsyncSession` transactions.
Execution must rely on existing internal domain services (e.g., `JobWorkService`, `GoodsReceiptService`) to ensure domain invariants (like stock constraints, custody ledgers, and Balance recalculations) are honored automatically.

## 8. Authorization Model
R-7 execution must derive its identity entirely from the `application_id` injected via the API layer (out-of-band). The CEM must independently authorize if the `application_id` has permission to execute Inventory mutations, without polluting the `AbstractEvidenceRequest`.

## 9. Event/Outbox Implications
All domain services in Inventory already utilize the Outbox pattern (e.g., `OutboundEventDispatcherService`). R-7 execution simply relies on these underlying services. Therefore, R-7 natively inherits reliable webhook generation without writing specific event-dispatching logic.

## 10. Proposed R-7 API Boundary
The current API contract does not strictly define if `ACTION` capabilities hit a dedicated execution route or share `/discover`.
**OPEN ARCHITECTURAL DECISION**: Does the CEM contract expect `ACTION` requests to route through a new endpoint (e.g., `POST /execute`), or are they routed identically to `POST /discover` but mapped to an execution handler internally?

## 11. Migration Strategy
There are no legacy R-7 handlers in Stage F (only RETRIEVE handlers exist in `ContextEngine`).
Migration involves writing net-new `R7ActionCapabilityHandler` instances mapping directly to `InventoryTransformationEngine`, `GoodsReceiptService`, etc., and injecting them into the `R4CapabilityRegistry` (or a dedicated execution registry).

## 12. Exhaustion/Certification Strategy
Certification requires proving that:
1. No mutation happens without validation.
2. The R-7 capability strictly executes the targeted domain service.
3. Errors bubble up reliably.
4. R-5 passthrough succeeds unconditionally.

## 13. Required Files to Create
- `src/domains/context/capabilities/r7_action_base.py`
- `src/domains/context/handlers/r7_action_handlers.py` (Or split by domain)
- `src/domains/context/resolvers/exception_resolver.py` (New R-5 resolver required for exception resolution)

## 14. Existing Files to Modify
- `src/domains/context/dependency_injection.py` (To inject execution handlers)
- `src/domains/context/semantic_resolvers.py` (To add Exception resolver)
- `src/api/v1/cem_router.py` (Depending on the architectural decision for routing ACTIONs).

## 15. Files that MUST remain untouched
- `src/domains/inventory/services/*` (All underlying business execution logic must remain untouched. The CEM adapts TO them).
- `ContextEngine` (Stage F compatibility).

## 16. Testing Strategy
Validate transaction rollbacks when Execution Limitations are met. Provide fake execution contexts and guarantee business-id mapping behaves deterministically.

## 17. Architectural Blockers
1. **Routing Boundary**: As highlighted in Section 10, the exact API entrypoint for `ACTION` execution vs `RETRIEVE` discovery is underspecified in the generic RABTA contract.
2. **Multiple URN Matches on Action**: How should R-7 behave if a request is ambiguous enough to trigger *both* Job Work Return and Purchase Return execution capabilities?

## 18. Recommended Implementation Sequence
**BLOCKED** pending Architectural Decision on Endpoint Routing. Once resolved:
1. Implement `R7ActionBase` capability interface.
2. Create `ExceptionSemanticResolver`.
3. Wrap `GoodsReceiptService` and `JobWorkService` as the first R-7 implementations.
4. Register inside Dependency Injection.
5. Certify Execution boundaries.

***
**FINAL STATUS:**
**R-7 BLOCKED — ARCHITECTURAL DECISION REQUIRED**
