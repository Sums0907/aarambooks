# R-6 ARCHITECTURE AUDIT — BRAIN CORE

**R-6 IMPLEMENTING AG WORKSPACE: AaramBooks Brain Core**

## 1. Authoritative Responsibility of R-6
R-6 (Progressive Query Expansion / Refinement Decision) is the orchestration phase responsible for managing the "One Bounded Refinement Loop." When an initial request to a Context Execution Module (CEM) yields ambiguous results (e.g., multiple candidates, missing context, or a need for broader scope), R-6 determines whether to safely expand the query, auto-resolve using conversational memory, or prompt the user for clarification. If a second pass is authorized, R-6 constructs the refined `AbstractEvidenceRequest` and re-invokes the CEM.

## 2. Why R-6 Belongs to Brain Core
R-6 represents cognitive decision-making and orchestration. The CEM is a physical execution boundary that merely reports business reality (e.g., "I found 3 entities matching 'blue bedsheets'"). It is the responsibility of Brain Core (RABTA) to decide how to handle that ambiguity conversationally. If the CEM made refinement decisions, conversational logic would become inextricably coupled to database schemas, violating the fundamental RABTA decoupling axiom.

## 3. Exact Boundaries
- **Brain Core:** Owns the cognitive orchestration lifecycle (R-2, R-3) and the ONE BOUNDED REFINEMENT policy.
- **R-4 (Business Discovery):** The CEM determines if it has the physical capability and data to fulfill the abstract request.
- **R-5 (Semantic Entity Resolution):** The CEM translates fuzzy semantic strings into its own physical identifiers (e.g., UUIDs), returning candidates if ambiguous.
- **R-6 (Progressive Expansion):** Brain Core inspects R-4/R-5 results. It makes the conversational/cognitive decision on how to refine the request and issues a targeted second pass.
- **R-7 (Business Execution):** The CEM exclusively owns state-changing business execution.

## 4. Handling Refinement/Clarification
When the CEM returns `MULTIPLE_CANDIDATES` or `CAPABILITY_AVAILABLE` (needs more instruction), R-6 evaluates the conversational state. If Brain Core has enough context (or if it pauses to ask the user to pick from a list), R-6 packages a second `AbstractEvidenceRequest`. This second request passes the chosen `business_id` in the `refinement_context`, allowing the CEM to bypass R-5 on the second pass and proceed directly to R-7 execution or R-4 data retrieval.

## 5. Interaction with R-5 Results
- **RESOLVED (`ENTITY_RESOLVED`, `EVIDENCE_AVAILABLE`):** R-6 is skipped. The execution loop terminates successfully.
- **AMBIGUOUS (`MULTIPLE_CANDIDATES`):** R-6 triggers. Brain decides to either auto-select a candidate based on prior context or prompt the user. A second pass is formulated.
- **NOT_FOUND (`ENTITY_NOT_FOUND`):** R-6 triggers to evaluate if the query can be safely broadened (e.g., dropping an optional filter). If it cannot be broadened, the loop terminates.

## 6. Consuming the R-5 UUID Passthrough
R-5 returns `CandidateEntity` objects containing opaque `business_id`s. R-6 must treat these `business_id`s as completely opaque tokens. It stores them in conversational memory and, upon refinement, simply injects the exact string into `AbstractEvidenceRequest.refinement_context`. Brain Core NEVER parses, validates, or infers schema from the UUID.

## 7. Existing R-6 Functionality in Brain Core
Currently, **none**. An audit of `src/brain_core/orchestration/rabta_orchestrator.py` reveals that `RabtaOrchestrator.process_query` is strictly a single-pass linear flow. It calls `cem_adapter.execute_evidence_request` once, passes the result to `id_provider.interpret_evidence`, and returns. The promised "One Bounded Refinement Loop" is architecturally defined in R-0 but remains unimplemented in code.

## 8. Existing Reusable Components
- `AbstractEvidenceRequest.refinement_context` (already modeled in `evidence_request_contracts.py`).
- `BusinessEvidenceResponse.resolved_candidates` (already modeled).
- `BusinessRealityStatus` enum (already modeled).

## 9. Architectural Gaps or Violations
- **Gap:** The orchestrator lacks a state machine or looping construct to pause for user input (clarification) and resume the same context, or to automatically trigger a second CEM pass.
- **Violation:** A `MULTIPLE_CANDIDATES` response currently terminates the loop as an interpreted final answer rather than triggering the bounded refinement loop.

## 10. Exact Files to Create/Modify
- **Modify:** `src/brain_core/orchestration/rabta_orchestrator.py` (Inject the bounded loop, state-pause/resume logic, and re-invocation).
- **Create:** `tests/rabta/test_r6_orchestration.py` (To rigorously prove the refinement loop works and is strictly bounded to ONE additional pass).

## 11. Files/Components that MUST Remain Untouched
- `src/shared/evidence_request_contracts.py` (The R-3 contract is already perfectly structured to support R-6).
- All CEM implementations (They already obey the contract).
- AaramIdentity.
- `RABTA-CEM-INTEGRATION-CONTRACT.md`.

## 12. Test Strategy and Certification Criteria
- **Bounded Enforcement:** A test must mock a CEM that perpetually returns `MULTIPLE_CANDIDATES`. The test must assert that the Orchestrator throws a loop-termination error or yields to the user after exactly ONE refinement pass, proving no infinite recursion exists.
- **Opaque Passthrough:** A test must prove that a `business_id` returned in pass 1 is injected unmodified into `refinement_context` in pass 2.

## 13. Exact Implementation Sequence
1. Update `RabtaOrchestrator.process_query` to evaluate `BusinessRealityStatus`.
2. Implement branching logic: if `MULTIPLE_CANDIDATES` or broadenable `ENTITY_NOT_FOUND`, construct the refined `AbstractEvidenceRequest`.
3. Implement the second CEM invocation (the bounded loop).
4. Implement strict counter/circuit-breaker to enforce the "one refinement only" rule.
5. Write and execute R-6 certification tests.

## 14. Information Sent Back to R-4/R-5
R-6 sends back a completely standard `AbstractEvidenceRequest`, with the singular addition of the `refinement_context` field populated with the selected opaque `business_id` or the explicit broadening instructions.

## 15. Confirmation of Non-Mutation
**CONFIRMED:** R-6 does not perform any business-state mutation. It is purely an orchestration layer within Brain Core designed to manipulate the semantic payload before a final R-7 execution pass.

---

**FINAL STATUS:**
`R-6 DESIGN READY FOR IMPLEMENTATION`
