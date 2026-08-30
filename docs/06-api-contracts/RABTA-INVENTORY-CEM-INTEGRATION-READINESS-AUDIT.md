# RABTA ↔ Aaram Inventory CEM Integration Readiness Audit

**Date:** 2026-08-30
**Scope:** Architectural read-only audit bridging `rabta-baseline-certified` (AaramBrain) and `aaram-inventory-cem-certified` (Aaram_Inventory).

---

## 1. Request Flow (RABTA → Inventory CEM)
- **Path:** Brain Core `ContextCapabilityGateway` → `HTTP POST /api/v1/context/resolve` → Inventory `ContextEngine`.
- **Payload:** `ContextCapabilityRequest` (contains `capability_urn` and `ResolvedSemanticRequirement` with `semantic_constraints`).
- **Nature:** Stateless, synchronous JSON-over-HTTP.

## 2. Response/Evidence Flow (Inventory CEM → RABTA)
- **Path:** Inventory `ContextEngine` → `HTTP 200/400` → Brain Core `InventoryCemAdapter`.
- **Payload:** `ContextCapabilityResult` (contains `status`, opaque `data` block, `provenance_metadata`, `error_message`).
- **Nature:** Brain Core is blind to the structure of `data`, storing it purely as evidence.

## 3. R-1 → R-11 Ownership Boundary
- **Brain Core (RABTA):** Owns R-1 (Understanding), R-2 (Classification), R-3 (Contracts), R-6 (Bounded Orchestration/Refinement), R-8 (Deterministic Interpretation), R-9 (Decision/Recommendation Safety), and R-10 (Memory Continuity). Zero business logic.
- **Inventory CEM:** Owns R-4 (Physical Discovery Mapping), R-5 (Semantic Entity Resolution to UUIDs), and R-7 (Business Execution / SQL Queries). Zero NLP.

## 4. Identity & Authorization Propagation
- **Auth Flow:** Brain Core blindly propagates the caller's JWT via the `Authorization` header.
- **Verification:** Inventory CEM natively enforces RBAC. The JWT must contain `"AARAM_BRAIN_APP"` in the `applications` list.
- **Physical Security:** Capability URNs map strictly to physical permissions (e.g., `urn:...:balance` requires `INVENTORY_PRODUCT_VIEW`).

## 5. R-9 → R-10 → R-7 Execution Path
- Intercepted mutative actions halt in Brain Core's `DecisionEngine` (R-9).
- They are persisted via `SuspendedExecutionState` (R-10).
- Upon explicit conversational confirmation, they are atomically consumed (Execute-Once) and dispatched to R-7 Action Adapters, which format them for CEM.

## 6. Proactive Recommendation Path
- `DecisionEngine` evaluates R-8 evidence (e.g., `open_exceptions > 0` from `exception_status`).
- Safe recommendations are generated and structurally presented.
- Execution requires the same R-9 confirmation loop as direct actions, enforcing user consent before any R-7 dispatch.

## 7. Capability Discovery Mapping
- **Inventory Supported URNs:**
  - `urn:aarambooks:inventory:capability:balance`
  - `urn:aarambooks:inventory:capability:ledger`
  - `urn:aarambooks:inventory:capability:jobwork_status`
  - `urn:aarambooks:inventory:capability:exception_status`

## 8. Semantic Entity Resolution Mapping
- Brain Core provides string identities (`inventory.entity.sku`, `inventory.entity.warehouse`).
- Inventory CEM accepts these and resolves them against real database rows using its internal `EntityResolutionResult` lifecycle, completely isolating Brain Core from database foreign keys.

## 9. Error and Execution-Limitation Propagation
- CEM returns explicit statuses (`DATA_UNAVAILABLE`, `UNAUTHORIZED`, `ERROR`).
- Brain Core `InventoryCemAdapter` maps these to exceptions or limitations.
- Orchestrator defers them to the R-8 Interpreter, ensuring the user receives a deterministic explanation (no generative AI guessing).

## 10. Executable vs Blocked Capabilities
- **Executable:** Read operations (Balance, Ledger, Jobwork, Exceptions).
- **Blocked:** All mutative operations (Transformations, Stock Adjustments). R-7 explicitly restricts these in the current release.

## 11. Known `evidence` vs `evidence_data` Inconsistency
- **Aaram Inventory State:** The certified CEM correctly outputs `{ "data": { ... } }` in `ContextCapabilityResult`.
- **RABTA State:** The `InventoryCemAdapter` still exhibits legacy behavior, erroneously packing this into a list called `evidence` instead of mapping it perfectly to `BusinessEvidenceResponse.evidence_data`.
- **Status:** Evaluated as **NON-BLOCKING**. The interpreter and decision engines actively normalize this discrepancy.

## 12. Actual Integration Blockers
- **NONE.** The JSON schemas, network protocols, and security layers perfectly decouple the cognitive system from the business system.

## 13. Production Readiness Gaps
- None for currently supported read capabilities. 
- Mutative operations must remain disabled until R-7 constraints are formally lifted and matching CEM action handlers are implemented.

---

### FINAL VERDICT
- **INTEGRATION READINESS:** READY
- **CERTIFICATION BLOCKERS:** NONE
- **NON-BLOCKING FINDINGS:** `evidence` vs `evidence_data` mapping discrepancy in `InventoryCemAdapter`.
- **EXACT NEXT IMPLEMENTATION STEP:** Complete infrastructure setup (networking/DNS) to physically route `ContextCapabilityGateway` traffic to the Aaram Inventory production CEM endpoint.
