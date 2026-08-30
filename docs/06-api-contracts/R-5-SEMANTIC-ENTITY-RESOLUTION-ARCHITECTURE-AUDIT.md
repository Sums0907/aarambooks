# R-5 SEMANTIC ENTITY RESOLUTION ARCHITECTURE AUDIT

## 1. Current R-5 Architecture
The current Semantic Entity Resolution logic within the AaramBooks Inventory Context Execution Module (CEM) is coordinated by `SemanticResolverRegistry`. It abstracts the mapping of semantic identities (e.g., `inventory.entity.sku`) to specific resolution implementations (e.g., `SKUSemanticResolver`). The registry exposes a `get_resolver(identity: str)` factory, and R-4 capabilities query this registry without knowing the underlying resolution mechanics. Currently, the system lacks resolvers for several required entities.

## 2. Existing Reusable Components
- **`SemanticResolverRegistry`**: The canonical entry point and factory for R-5. Highly reusable and currently enforces the correct architectural boundary.
- **`SemanticResolver` Protocol**: Defines the internal API contract (`async def resolve(self, semantic_value: Any, target_type: str) -> EntityResolutionResult`).
- **`EntityResolutionResult`**: A strongly typed DTO used universally to standardize resolution responses.

## 3. Complete Entity Resolver Census
Based on current R-4 usage across Balance, Ledger, and Jobwork Status capabilities, the following physical entities represent the complete surface for R-5:

### A. SKU (`inventory.entity.sku`)
- **Semantic Key**: `inventory.entity.sku`
- **Physical Identifier**: UUID (`id` in `SKUModel`)
- **Source of Truth**: `SKUModel` (`src/domains/masters/models/sku.py`)
- **Resolver Existence**: YES (`SKUSemanticResolver`)
- **Matching Mechanism**: Exact matches against `item_code`, `sku_code`, `shopdeck_sku_id`, or `barcode`. No fuzzy matching or UUID parsing fallback.
- **Ambiguity Behavior**: Returns `AMBIGUOUS` with raw UUID candidate list.
- **Authorization**: Global catalog read, no row-level application isolation required for resolution.
- **Current Status**: Implemented and bounded correctly.

### B. Warehouse (`inventory.entity.warehouse`)
- **Semantic Key**: `inventory.entity.warehouse`
- **Physical Identifier**: UUID (`id` in `WarehouseModel`)
- **Source of Truth**: `WarehouseModel` (`src/domains/masters/models/warehouse.py`)
- **Resolver Existence**: NO (Causes `RESOLUTION_UNAVAILABLE` fallback in `ContextEngine`)
- **Matching Mechanism Needed**: Exact matches against `warehouse_code` or `warehouse_name`.
- **Authorization**: Global read, no row-level access restriction for resolution.
- **Current Status**: BLOCKED / MISSING.

### C. Job Worker (`inventory.entity.job_worker`)
- **Semantic Key**: `inventory.entity.job_worker`
- **Physical Identifier**: UUID (`id` in `Supplier` where `is_job_worker == True`)
- **Source of Truth**: `Supplier` (`src/domains/masters/models/supplier.py`)
- **Resolver Existence**: NO
- **Matching Mechanism Needed**: Exact matches against `name` or `gstin`, rigorously filtered by `is_job_worker == True`.
- **Authorization**: Global read, no row-level restriction.
- **Current Status**: BLOCKED / MISSING.

## 4. Canonical R-5 Responsibility
**R-5 answers exactly one question:** *"Which physical Inventory business entity UUID does this semantic reference represent?"*
R-5 DOES NOT determine intent, formulate conversation, determine capability compatibility, or interpret CEM routing.

## 5. Canonical Resolver Interface
```python
class SemanticResolver(Protocol):
    async def resolve(
        self, 
        semantic_value: Any, 
        target_type: str,
        # authorization_context: Optional[AaramIdentity] = None 
        # (Only if row-level security applies. Currently unneeded for SKU/Warehouse/Supplier)
    ) -> EntityResolutionResult:
        ...
```

## 6. Resolution Statuses
- `RESOLVED`: Exactly one physical entity matches. Returns the opaque business ID.
- `AMBIGUOUS`: More than one physical entity matches. Returns multiple candidate business IDs.
- `NOT_FOUND`: Zero entities match the semantic value.
- `INVALID`: The requested `target_type` is not supported by the resolver.
- `RESOLUTION_UNAVAILABLE`: R-5 lacks a registered resolver for the given semantic key.

## 7. Ambiguity Model
If multiple entities match (e.g., identical names), R-5 returns `ResolutionStatus.AMBIGUOUS` and populates the `candidates` list with opaque physical UUIDs. **Crucially**, R-5 makes no attempt to prompt the user or apply conversational context to break the tie. It pushes the ambiguity back to Brain Core.

## 8. R-4 / R-5 Boundary
- **R-4 (Discovery/Execution)** determines *applicability*. It asks R-5 to translate semantic entities, and fails/routes based on the `ResolutionStatus`. R-4 is purely an orchestration layer.
- **R-5 (Resolution)** is a pure translation layer. It is unaware of the requesting capability and does not parse `AbstractEvidenceRequest`.

## 9. R-5 / R-7 Boundary
R-5 remains fully detached from state-changing operations. It operates entirely as read-only queries against master repositories. R-7 capabilities will utilize R-5 through the same `SemanticResolverRegistry` interface used by R-4.

## 10. AaramIdentity / Application Authorization Boundary
Entity resolution inside the Inventory domain queries global master catalogs (SKU, Warehouse, Job Worker). Currently, there is no requirement to inject `application_id` or `AaramIdentity` into the `resolve()` signature because there is no row-level tenant isolation applied to these entity lookups. CEM URNs and `id_urn` remain strictly in the routing layer and must not enter the semantic value payload.

## 11. Refinement Compatibility
If Brain Core issues a refinement request (R-6), it may send back a previously resolved physical UUID. R-5 resolvers must be capable of recognizing when `semantic_value` is already a physical UUID (the requested `target_type`) and bypass semantic lookup, directly echoing it back.
*Architectural Weakness:* The current `SKUSemanticResolver` does not check if `semantic_value` is already a UUID.

## 12. Legacy Stage F Migration Strategy
The legacy Stage F pipeline currently handles missing resolvers by falling back to `uuid.UUID()` casting inside the execution handlers. This leaks physical UUID fallback logic into R-4/Stage F. We must remove this fallback from the capability orchestration layer and centralize it inside R-5. 

## 13. Required New Files
- `src/domains/context/resolvers/warehouse_resolver.py`
- `src/domains/context/resolvers/job_worker_resolver.py`

## 14. Existing Files Requiring Modification
- `src/domains/context/semantic_resolvers.py` (Break out resolvers into separate files for scaling).
- `src/domains/context/dependency_injection.py` (Register the new resolvers).

## 15. Existing Files That Must Remain Untouched
- `src/shared/evidence_request_contracts.py`
- `docs/06-api-contracts/RABTA-CEM-INTEGRATION-CONTRACT.md`
- `src/domains/context/services/r4_discovery_service.py` (R-4 remains frozen).

## 16. Test Strategy
- Create `test_r5_warehouse_resolver.py`.
- Create `test_r5_job_worker_resolver.py`.
- Enforce the "UUID Passthrough" rule via test assertions.
- Verify `is_job_worker` filter logic heavily for Job Workers.

## 17. Architectural Blockers
1. **UUID Passthrough**: Resolvers currently do not elegantly handle physical UUIDs passed in as semantic values (refinement loops). We need a consistent R-5 rule to handle this.
2. **Missing Resolvers**: `inventory.entity.warehouse` and `inventory.entity.job_worker` lack resolvers, forcing handlers to perform illegal UUID conversions.

## 18. Proposed Implementation Sequence
1. Implement UUID Passthrough base logic for all resolvers to support refinement.
2. Implement and register `WarehouseSemanticResolver`.
3. Implement and register `JobWorkerSemanticResolver`.
4. Delete UUID fallback logic illegally housed inside `ContextEngine` or existing handlers.
5. Certify R-5.

***

**FINAL STATUS:**
R-5 DESIGN READY FOR IMPLEMENTATION
