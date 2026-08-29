# R-10 Orchestrator Integration Design Audit

## 1. ORCHESTRATOR MEMORY ENTRY
Memory must be loaded at the very beginning of the `RabtaOrchestrator.process_query` cycle, prior to invoking R-1 (`extract_understanding`). 
- **Session Identification:** A unique combination of `tenant_id`, `client_id`, `user_id` (extracted from `auth_context`), and a distinct conversational `session_id`.
- **State Needed:** A serialized array of prior `ConversationTurn`s and any active `clarification_options`.
- **Never Loaded:** Authoritative business evidence or CEM capabilities.
- **Absence of Memory:** The orchestrator degrades gracefully into a stateless query.
- **Semantic Impact:** The R-4→R-8 execution semantics remain identical. Memory merely provides historical context to the Intelligence Domain during R-1 parsing; the orchestrator's generic routing does not change.

## 2. TURN PERSISTENCE
Following a successful R-8 (`interpret_evidence`) return, the orchestrator must persist exactly one `ConversationTurn`.
- **Persisted:** The raw user `query` and the resulting `ConversationalResponse`.
- **Distinctions:**
  - *Ordinary History:* Stored as sequential `ConversationTurn` objects for dialogue context.
  - *Suspended Action:* Stored explicitly as a `SuspendedExecutionState` with a unique nonce and TTL.
  - *Business Evidence:* `BusinessEvidenceResponse.evidence_data` is explicitly excluded from persistence. Only the interpreted text and UI render directives within the `ConversationalResponse` are saved.

## 3. SUSPENDED ACTION LIFECYCLE
- **PENDING:** R-9 (via the Intelligence Domain) intercepts an action and suspends it in R-10, returning a confirmation prompt to the user.
- **Retrieve:** Upon the user's reply, R-9 queries R-10 using the `session_id` to retrieve the pending request.
- **User Confirmation:** R-9 verifies the user's intent is affirmative.
- **Atomic Consume:** The orchestrator (or R-9 via the MemoryProvider) attempts to atomically consume the nonce.
- **R-7 Execution:** If consumption succeeds, the orchestrator bypasses R-4/R-5 and routes the retrieved `AbstractEvidenceRequest` directly to R-7.
- **Ownership:** R-9 owns the cognitive confirmation logic. R-10 owns the persistence/consumption guarantees. The Orchestrator owns the routing.

## 4. ATOMIC CONSUMPTION
The `MemoryProvider.atomic_consume_action` boolean abstraction is sufficient to guarantee execution safety across concurrent requests. 
- **Concrete Persistence Requirement:** The underlying PostgreSQL adapter must implement this using a locking atomic update, e.g., `UPDATE ... SET status = 'CONSUMED' WHERE nonce = ? AND status = 'PENDING' RETURNING id`. A simple `SELECT` followed by an `UPDATE` in application memory is prohibited as it creates a race condition for duplicate execution.

## 5. SESSION/TENANT ISOLATION
- **Boundary:** Memory isolation is strictly defined by the composite key of `tenant_id`, `user_id`, and `session_id`.
- **Architectural Gap:** While `session_id` is present in the `SuspendedExecutionState` contract, the `tenant_id` and `user_id` must also be explicitly validated during `retrieve_suspended_action` to prevent cross-tenant nonce guessing attacks. The orchestrator must enforce this auth binding when querying the memory adapter.

## 6. ORCHESTRATOR BOUNDARY
Adding R-10 integration into `RabtaOrchestrator` does not violate its purity. 
- **Rule:** The orchestrator acts merely as a conduit, loading the generic `ConversationTurn` history and passing it into R-1, and retrieving the generic `ConversationalResponse` from R-8 to save it. The orchestrator performs zero semantic resolution or business logic on the memory payload itself.

## 7. FAILURE SEMANTICS
- **Unavailable Memory:** Orchestrator proceeds as a stateless turn.
- **Malformed State:** Orchestrator drops the corrupted history and proceeds statelessly.
- **Expired/Wrong Session:** R-10 returns `None`; R-9 responds that the action expired.
- **Atomic Consumption Fails:** Execution is blocked; prevents double mutation.
- **Persistence Fails post-R-7:** The business action (e.g., Goods Receipt) was successfully committed by the CEM, but the conversational turn failed to save. This desyncs dialogue history slightly, but prevents double execution. This is an acceptable failure mode.

## 8. MINIMUM IMPLEMENTATION SCOPE
- **Production Files:** Modifying `src/brain_core/orchestration/rabta_orchestrator.py` to accept a `MemoryProvider` dependency, load context, and persist `ConversationTurn`s.
- **Tests:** Update `test_orchestrator.py` to verify memory load/save hooks are called.
- **Contracts:** No new contracts required; leverage the already implemented R-10 foundation.
- **Explicitly UNCHANGED:** R-4, R-5, R-6, R-7, and R-8 logic must remain completely untouched.

---

## Findings
Integrating R-10 into the `RabtaOrchestrator` is a mathematically safe operation that respects all boundaries. It provides the necessary stateful context for R-1 (anaphoric resolution) without injecting business caching or schema leakage into Brain Core.

## Boundary Decision
The Orchestrator strictly manages the injection and persistence of the generic state containers. All cognitive reasoning regarding that state remains within the applicable Intelligence Domain (R-1, R-8, R-9).

## Minimum Required Implementation
1. Inject `MemoryProvider` into `RabtaOrchestrator`.
2. Add a `session_id` parameter to `process_query`.
3. Load `ConversationTurn` history and supply it to `extract_understanding`.
4. Wrap `interpret_evidence` output into a `ConversationTurn` and persist it.

## Certification Impact
R-10 integration maintains the certification of R-4→R-8. The generic contracts remain intact, and state mutation guarantees are securely enforced by the atomic consumption boundary.

## Exact Next Implementation Workspace and Step
**Workspace:** AaramBrain
**Step:** Implement memory injection and persistence within `src/brain_core/orchestration/rabta_orchestrator.py` according to the minimum scope defined.
