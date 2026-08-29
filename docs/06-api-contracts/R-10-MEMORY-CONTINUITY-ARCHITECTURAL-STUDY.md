# R-10 Memory & Continuity Architectural Study

## 1. Exact Responsibility of R-10
R-10 (Memory & Continuity) is responsible for maintaining short-term conversational context across discrete user interactions (inter-turn). It allows the system to resolve anaphoric references (e.g., "Receive 50 of *it*"), track the progress of multi-step decision trees, and pause/resume workflows (e.g., awaiting explicit user confirmation before executing a destructive action).

## 2. Conversational Memory vs. Business State
- **Conversational Memory:** The state of the dialogue. Includes user utterances, pending intents, clarification options presented, and previously resolved entity references.
- **Business State:** The authoritative truth of the domain (e.g., actual inventory levels, committed Goods Receipts). 
- **Boundary Rule:** R-10 stores conversational memory. It must *never* act as a cache or shadow for business state.

## 3. What R-10 May Persist
- Previous user queries and system responses (`ConversationalResponse`).
- Opaque `business_id`s successfully resolved in previous R-5 passes (to avoid forcing the user to repeatedly disambiguate the same SKU).
- Pending `AbstractEvidenceRequest` payloads that have been halted by R-9 awaiting user confirmation.
- The active `clarification_options` presented by R-8 (so a user saying "The first one" can be mapped deterministically to a `business_id`).

## 4. What R-10 Must Never Persist
- Large `BusinessEvidenceResponse.evidence_data` payloads (this would inadvertently create a stale shadow database).
- Any attempt to cache business rules or CEM capability availability (capabilities must be freshly discovered via R-4).

## 5. Memory Scoping
Memory must be strictly isolated hierarchically: `Tenant/App ID (via Auth Context)` -> `User ID` -> `Conversation/Session ID`. Cross-session or cross-tenant memory leakage is a critical security violation. 

## 6. Retrieval and Supply
Memory is retrieved at the very beginning of a turn. It is injected into the Intelligence Domain (ID) context window so R-1 can correctly parse the new intent with historical awareness. It is also inspected by the Orchestrator to see if the user is currently answering a direct R-9 confirmation prompt.

## 7. R-10 Interaction with R-6 (Bounded Refinement)
R-6 operates *intra-turn* (within a single orchestration lifecycle). R-10 operates *inter-turn* (across separate user messages). R-10 merely records the final outcome of the R-6/R-7 execution loop at the end of the turn. They do not intersect.

## 8. R-10 Interaction with R-8 (Interpretation)
R-10 persists the `ConversationalResponse` produced by R-8. Critically, it persists the `clarification_options` list so that opaque business IDs are kept in Brain Core's short-term memory, ready to be attached to the next R-3 Evidence Request if the user selects one.

## 9. R-9 Dependency on R-10
R-9 (Decision & Action) absolutely requires R-10 to function. For R-9 to pause execution and ask "Are you sure you want to adjust stock?", R-10 must serialize and persist the fully-formed `AbstractEvidenceRequest`. When the user replies "Yes", R-9 reads the suspended request from R-10 and dispatches it directly to R-7, bypassing the need to re-parse and re-classify via R-1/R-2.

## 10. Required Shared Contracts
A formal contract for conversational state is required. This likely takes the form of a `ConversationTurn` model containing:
- Timestamp
- User utterance
- Suspended `AbstractEvidenceRequest` (if applicable)
- Produced `ConversationalResponse`

## 11. Existing Persistence Abstractions
Brain Core already possesses foundational memory interfaces (`src/brain_core/memory/test_interfaces.py` and `src/infrastructure/adapters/postgres_memory.py` observed in the test suite). These abstractions must be validated to ensure they support the new R-10 specific persistence needs (like suspending an `AbstractEvidenceRequest`).

## 12. Security, Isolation, Expiry, and Lifecycle
Memory must be ephemeral. To prevent users from accidentally confirming a destructive action requested days ago, a strict Time-To-Live (TTL) or inactivity expiry (e.g., 2 hours) must be enforced on pending R-9 actions.

## 13. Deterministic vs Intelligence-Bearing
R-10 is purely **deterministic infrastructure** (storage/retrieval). It performs zero cognitive reasoning. The Intelligence Domain (R-1/R-9) applies reasoning *to* the memory, but the memory layer itself is a dumb datastore.

## 14. Exact Implementation Boundaries
- **R-10 Owns:** Storage, retrieval, and TTL expiry of conversational context.
- **R-10 Prohibited from:** Altering the request, interacting with CEMs, applying business logic, or resolving entities.

## 15. Exact Dependencies and Implementation Order
1. **R-10 Contracts:** Define `ConversationContext` and `SuspendedAction` contracts.
2. **R-10 Infrastructure:** Update the existing Brain Core memory interfaces to support saving/loading these new contracts.
3. **Orchestrator Integration:** Update `RabtaOrchestrator` to load context at the start of a turn and save context at the end.
4. **R-9 Integration:** Once memory exists, implement R-9 to utilize it for multi-turn confirmations.

---

## Findings
R-10 is purely deterministic infrastructure that solves the multi-turn statelessness of the current R-1→R-8 loop. It must strictly persist conversational context and suspended execution requests without caching authoritative business state.

## R-10 Ownership Boundary
R-10 belongs to Brain Core infrastructure. It is domain-agnostic and schema-agnostic.

## R-9 Dependency Requirements
R-9 cannot exist without R-10. R-9 requires R-10 to serialize and persist an `AbstractEvidenceRequest` across a conversational boundary so that execution can be paused for user confirmation and resumed without data loss.

## Architectural Blockers
None. The architecture cleanly supports the addition of a state-persistence layer.

## Required Contracts
New Pydantic models are required in `src/shared/` to represent a `ConversationSession`, `ConversationTurn`, and `SuspendedExecutionState`.

## Required Implementation Steps
1. Define the R-10 memory contracts.
2. Implement or adapt the Brain Core MemoryAdapter (e.g., Redis or Postgres) to support these contracts.
3. Integrate the MemoryAdapter into the `RabtaOrchestrator` lifecycle.

## Exact Next Implementation Workspace and Step
**Workspace:** AaramBrain
**Step:** Define the R-10 state contracts (`ConversationSession`, `SuspendedExecutionState`) in the shared contracts directory and adapt the existing memory interfaces.

## R-10 Readiness Decision
R-10 READY FOR ARCHITECTURAL DESIGN
