# R-9 Single-Pass Execution-Flow Audit

## 1. Incoming-Turn Boundary
- **Entry Point:** A new conversational turn enters Brain Core via `RabtaOrchestrator.process_query()`.
- **R-10 History Loading:** Generic `ConversationTurn` history is loaded inside `process_query()` strictly *before* calling `R-1` (`extract_understanding`), allowing the Intelligence Domain to use past turns for anaphoric resolution.
- **Suspended Action Inspection:** A pending `SuspendedExecutionState` can be directly inspected by querying the `MemoryProvider` for an active nonce tied to the current `session_id`. This inspection should occur immediately after `R-1`/`R-2` to intercept the flow before `R-6/R-7`.

## 2. Confirmation Recognition
Trace of the R-1→R-3 pipeline:
- **"Yes":** R-1 outputs `ConversationalUnderstanding` with an explicit intent (e.g., `ConversationalIntent.CONFIRMATION`).
- **"No":** R-1 outputs `ConversationalUnderstanding` with `ConversationalIntent.REJECTION`.
- **"Actually make it 40":** R-1 recognizes an operational intent (`ConversationalIntent.ACTION`), completely disjoint from the pending confirmation. The R-10 suspended action is ignored (or explicitly rejected) and a fresh `AbstractEvidenceRequest` is constructed.
- **"What is the current stock?":** R-1 recognizes a read intent (`ConversationalIntent.QUERY`). The suspended action remains pending until TTL expiry, while the query executes statelessly.

## 3. R-9 Interception Point
R-9 operates at two distinct interception points within the `RabtaOrchestrator`:
- **Pre-Execution Interception (Between R-3 and R-6/R-7):** R-9 inspects the newly constructed `AbstractEvidenceRequest`. If the request is destructive (e.g., mutation), R-9 halts the pipeline, suspends the request via R-10, and yields control to R-8 to request confirmation. Alternatively, if the user input is a "Yes", R-9 intercepts here to retrieve the suspended request.
- **Post-Execution Interception (After R-7, Before R-8):** R-9 inspects the `BusinessEvidenceResponse` returned by R-7 to generate structured, proactive recommendations before R-8 generates the final natural language.

## 4. Suspended-Request Resumption
The `SuspendedExecutionState` holds the exact, immutable `AbstractEvidenceRequest` generated during the original turn. When a confirmation is recognized, R-9 retrieves this state and passes the `.request` payload *directly* to R-6/R-7. 
R-9 MUST NOT reconstruct, alter, or inject parameters into the suspended request. If any parameters need changing, it ceases to be a confirmation and becomes a fresh execution.

## 5. Atomic Consumption
**Exact Safe Ordering:**
1. R-9 retrieves the suspended action (based on active session state).
2. R-9 validates the user's intent is an explicit `CONFIRMATION`.
3. R-9 (via the Orchestrator) calls `atomic_consume_action(nonce, session_id)`.
4. Only if `True` is returned, the Orchestrator proceeds to R-7 Execution with the retrieved request.

**Sufficiency:** The current R-10 `atomic_consume_action(nonce, session_id) -> bool` contract is structurally sufficient to guarantee execute-once semantics and prevent concurrent replay attacks.

## 6. Recommendation Path
After R-7 returns a `BusinessEvidenceResponse` (e.g., "Stock is 5 units"), R-9 analyzes this evidence. It may decide to recommend an action (e.g., "Reorder 50 units").
R-9 constructs a fully-formed `AbstractEvidenceRequest` for this proactive action, calls `suspend_action` on R-10 to obtain a secure `nonce`, and embeds this nonce into a structured `Recommendation` payload passed to R-8. R-8 renders this as "Stock is 5 units. Would you like me to reorder 50 units?" R-7 is entirely bypassed during recommendation generation.

## 7. Orchestrator Ownership
Based strictly on the existing architecture (where generic tasks like classification are handled by dedicated dependencies injected into `RabtaOrchestrator`, e.g., `RequirementClassifier`), R-9 should NOT be hardcoded into the orchestrator.
R-9 must be exposed through a dedicated provider/service (e.g., a `DecisionEngine`) that is injected into `RabtaOrchestrator`. The Orchestrator delegates the safety decision to this engine.

## 8. Boundary Violations
The R-9 design must carefully avoid:
- **Duplicating R-6 Refinement:** R-9 must not attempt to resolve missing parameters.
- **Duplicating R-7 Execution:** R-9 must not hit CEMs to validate stock or capabilities.
- **Duplicating R-8 Language Generation:** R-9 must emit structured types (e.g., `ConfirmationRequired(nonce)`), not strings like "Are you sure?".
- **R-10 as Business Truth:** R-9 must not read `evidence_data` from R-10.
- **Implicit Confirmation:** R-9 must strictly demand `ConversationalIntent.CONFIRMATION`.
- **Mutating Suspended Requests:** R-9 must treat the suspended `AbstractEvidenceRequest` as entirely immutable.

## 9. Minimum Implementation Surface
- `src/brain_core/decision/decision_engine.py` (New generic engine)
- `src/shared/decision_contracts.py` (New structured payloads)
- `src/brain_core/orchestration/rabta_orchestrator.py` (Inject engine, add interception points)
- `src/shared/conversational_contracts.py` (Add `CONFIRMATION`/`REJECTION` intents)
- Tests for the `DecisionEngine` and updated `RabtaOrchestrator`.

## 10. Final Decision
R-9 READY FOR IMPLEMENTATION

---

## Findings
The R-9 Decision & Action layer is structurally sound and integrates perfectly into the existing RABTA pipeline via the `RabtaOrchestrator`. The execute-once safety guarantees are fully supported by the R-10 foundation.

## R-9 Boundary Decision
R-9 is a dedicated `DecisionEngine` injected into the Orchestrator. It owns cognitive safety (requiring confirmation) and proactive recommendations, but emits only structured state, relying on R-8 for language and R-7 for mutation.

## Exact Implementation Prerequisites
R-10 is fully implemented and certified. R-4 through R-8 are frozen. The path is clear.

## Exact Production Files Expected to Change
- `src/shared/conversational_contracts.py`
- `src/shared/decision_contracts.py` (New)
- `src/brain_core/decision/decision_engine.py` (New)
- `src/brain_core/orchestration/rabta_orchestrator.py`

## Exact Next Implementation Step
**Workspace:** AaramBrain
**Step:** Define the R-9 structural contracts (`DecisionResponse`, `ConfirmationRequired`, `Recommendation`) in `src/shared/decision_contracts.py` and extend `ConversationalIntent` in `conversational_contracts.py`.
