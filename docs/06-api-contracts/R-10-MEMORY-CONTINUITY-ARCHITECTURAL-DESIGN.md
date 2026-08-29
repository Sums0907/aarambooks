# R-10 Memory & Continuity Architectural Design

## 1. R-10 STATE MODEL
The state model for R-10 defines strictly isolated conversational persistence primitives:
- **ConversationSession**: The top-level container tracking `tenant_id`, `user_id`, and session boundaries.
- **ConversationTurn**: A sequential record containing the user's natural language input, the generated `ConversationalResponse`, and a timestamp.
- **SuspendedExecutionState**: A serialized `AbstractEvidenceRequest` paused by R-9, containing a unique `nonce`, expiry timestamp, and status (e.g., `PENDING_CONFIRMATION`).
- **Clarification State**: The active `clarification_options` presented to the user, allowing ordinal ("The first one") or direct mapping to a `business_id` in the subsequent turn.
- **Prior Resolved Entity References**: Historical map of semantic terms to opaque physical `business_id`s established in earlier R-5 passes.

## 2. STATE OWNERSHIP
- **Creation**: The Brain Core Orchestrator creates ConversationTurns and SuspendedExecutionStates. R-8 defines the Clarification State.
- **Reads**: Brain Core loads memory at the start of a turn and injects it into the Intelligence Domain (for R-1 contextual parsing). R-9 reads SuspendedExecutionStates to evaluate user confirmations.
- **Updates**: Brain Core Orchestrator updates a SuspendedExecutionState from `PENDING` to `CONSUMED` during execution.
- **Deletion/Expiry**: Managed entirely by the R-10 underlying storage infrastructure via Time-To-Live (TTL).

## 3. BUSINESS-TRUTH BOUNDARY
**Explicit Prohibition:** R-10 must NEVER persist authoritative business data.
R-10 cannot become:
- A business database.
- A business-evidence cache (caching stock balances or ledger entries).
- A CEM capability cache (capabilities must be freshly discovered via R-4).
- A second entity-resolution store (R-5 exclusively owns string-to-UUID mapping; R-10 merely remembers what R-5 previously resolved within the session context).

## 4. MULTI-TURN LIFECYCLE
**Standard Conversational Turn:**
`User Utterance → Memory Load → R-1/R-2/R-3 → R-4/R-5/R-6/R-7 → R-8 → Memory Persistence (ConversationTurn)`

**Suspended Action Lifecycle:**
`Proposed by R-9 → R-10 Suspend (Awaiting Confirmation) → User Replies "Yes" → R-10 Read & Consume → Dispatch to R-7 → Executed`
OR
`User Replies "No" → R-10 Mark Rejected`
OR
`Time Elapses → R-10 TTL Expiry`

## 5. CRITICAL R-9 QUESTION: SUSPENDED EXECUTION SAFETY
When an `AbstractEvidenceRequest` is suspended by R-9 and subsequently confirmed by the user, the architectural rules are:
- **Direct Execution:** The request MAY be dispatched directly to R-7 execution, bypassing R-1/R-2/R-4.
- **Authorization Revalidation:** The incoming request token (JWT) MUST be revalidated against the required CEM capability. 
- **Context Revalidation:** The `tenant_id` and `user_id` MUST exactly match the suspended state.
- **Entity Resolution Revalidation:** Physical UUIDs resolved during the initial R-5 pass do NOT need revalidation. They are immutable business identifiers.
- **Business Truth Re-read:** R-10/R-9 must NOT re-read business state. R-7 domain services remain strictly responsible for atomicity and validation (e.g., preventing negative stock) at the moment of execution.
- **Immutable Identity:** The suspended request MUST possess a unique, cryptographically secure `nonce`.
- **Duplicate Prevention:** R-10 MUST implement atomic consumption (`consume_action(nonce)`). The state must be atomically marked consumed or deleted *before* the request is handed to R-7.

## 6. TTL / EXPIRY
- **Ordinary Conversational Memory:** 24 hours of inactivity.
- **Clarification Options:** 1 hour.
- **Suspended Destructive Actions:** 5–15 minutes (Requires Product Approval). Short expiry prevents users from accidentally executing stale, out-of-context destructive actions.

## 7. STORAGE ABSTRACTION
The existing `MemoryProvider` interface in `src/brain_core/memory/interfaces.py` (which supports `read_memory` and `write_memory` using tags/metadata) can be partially reused. 
- **Extension Required:** It must be extended to support atomicity (e.g., `atomic_consume_state(nonce)`) and explicit TTLs. 
- **Implementation Agnosticism:** The abstraction must not assume Redis or Postgres directly; the implementation adapter fulfills the contract.

## 8. SERIALIZATION
`AbstractEvidenceRequest`, `ConversationalResponse`, and `ConversationalUnderstanding` are all Pydantic models. They must be strictly serialized to JSON for storage. If schema versions change, malformed deserialization must gracefully fail the memory load rather than crashing the orchestrator.

## 9. SECURITY
- **Tenant/App Isolation:** Memory keys/tags MUST strictly partition data by `tenant_id` and `client_id`.
- **User Isolation:** Memory MUST be isolated by `user_id`.
- **Session Isolation:** Memory MUST be isolated by `session_id`.
A user in one session cannot confirm an action suspended in a different session, nor can tenants cross-pollinate.

## 10. FAILURE SEMANTICS
- **Memory is unavailable:** The system degrades gracefully to a stateless transaction mode.
- **Malformed state:** Discarded immediately; treated as an empty session.
- **Suspended state has expired:** Confirmation is rejected. The user is informed the request expired and must start over.
- **Confirmation of unknown state:** Rejected cleanly by R-9.
- **State belongs to another context:** Authorization failure.

## 11. R-9 INTERFACE
R-9 will require the following capabilities from R-10:
- `suspend_action(request: AbstractEvidenceRequest, ttl: int) -> str (nonce)`
- `retrieve_suspended_action(nonce: str) -> Optional[AbstractEvidenceRequest]`
- `atomic_consume_action(nonce: str) -> bool`

## 12. IMPLEMENTATION ORDER
1. Extend `MemoryProvider` interface with TTL and atomic consumption methods.
2. Define Pydantic serialization models for `ConversationTurn` and `SuspendedExecutionState`.
3. Integrate the updated `MemoryProvider` into `RabtaOrchestrator` to inject history prior to R-1 and persist turns post-R-8.
4. Implement the R-10 R-9 Interface (`suspend_action`, `atomic_consume_action`).

---

## Findings
R-10 is the foundational enabler for multi-turn conversational intelligence. By strictly defining memory as a serialized orchestration state rather than a business data cache, we preserve the purity of the RABTA framework.

## Approved R-10 State Model
R-10 manages `ConversationSession`, `ConversationTurn`, `SuspendedExecutionState`, `ClarificationState`, and resolved entity reference mappings.

## R-10 Ownership Boundary
R-10 is purely generic Brain Core infrastructure. It possesses no domain intelligence, does not interact with CEMs, and cannot query the authoritative business databases.

## R-9 Dependency Contract
R-9 depends on R-10 to provide secure, TTL-bound, atomic storage of `AbstractEvidenceRequest` payloads awaiting explicit user confirmation.

## Security Rules
Total isolation by `tenant_id`, `user_id`, and `session_id`. Atomic consumption of nonces is mandatory for execution resumption.

## Lifecycle Rules
Memory is loaded before R-1 and persisted after R-8. Suspended actions exist in a PENDING state until confirmed (consumed), rejected (deleted), or expired (TTL).

## Storage Decision
Extend the existing generic `MemoryProvider` interface. Do not couple the orchestration directly to Redis/Postgres.

## Architectural Blockers
None. The architecture natively accommodates a generic persistence provider injecting state into the orchestrator.

## Required Implementation Steps
1. Extend `MemoryProvider` interface in `src/brain_core/memory/interfaces.py`.
2. Create R-10 Pydantic contracts in shared logic.
3. Integrate memory lifecycle hooks into `RabtaOrchestrator`.

## Exact Next Implementation Workspace and Step
**Workspace:** AaramBrain
**Step:** Extend the `MemoryProvider` interface in `src/brain_core/memory/interfaces.py` and define the R-10 state contracts (`ConversationTurn`, `SuspendedExecutionState`).

## R-10 Implementation Readiness Decision
R-10 READY FOR ARCHITECTURAL DESIGN
