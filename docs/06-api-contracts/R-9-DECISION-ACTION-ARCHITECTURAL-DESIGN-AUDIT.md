# R-9 Decision & Action Architectural Design Audit

## 1. R-9 RESPONSIBILITY
R-9 owns the cognitive logic for conversational decision-making, primarily focusing on determining whether a fully-resolved user intent is safe to execute, requires explicit confirmation, or warrants a proactive recommendation based on the outcome of a query.
- **R-9 Owns:** Evaluating `AbstractEvidenceRequest`s for destructive nature, requesting confirmation, parsing user confirmation/rejection of pending actions, and proposing proactive recommendations (e.g., suggesting a restock after a low-stock query).
- **Outside R-9 (Strictly Excluded):** 
  - *R-6 Refinement:* Resolving missing parameters, ambiguous entities, or capability mapping. (R-6 ensures the request is well-formed; R-9 ensures it is safe to run).
  - *R-7 Execution:* Interacting with the business system (CEM).
  - *R-8 Interpretation:* Generating natural language text. (R-9 emits structured state; R-8 turns it into English).
  - *R-10 Persistence:* Storing the suspended actions or conversation history. R-9 merely asks R-10 to suspend or consume.

## 2. MULTI-TURN DECISION FLOW
1. **User request:** "Receive 50 units of SKU-123"
2. **RABTA Interpretation (R-1→R-6):** Resolves into a complete `AbstractEvidenceRequest` for mutation.
3. **Decision Required (R-9):** R-9 intercepts the request before R-7, flags it as destructive, and demands confirmation.
4. **R-10 Suspended State:** The orchestrator delegates to R-10 to persist the `SuspendedExecutionState` with a unique nonce.
5. **Confirmation Question (R-8):** R-8 formats the suspension into: "Are you sure you want to receive 50 units?"
6. **User's next turn:** "Yes"
7. **Retrieval:** Orchestrator loads R-10 history; R-1 parses the intent as an affirmative response.
8. **Confirmation Decision (R-9):** R-9 detects the active suspension, matches the affirmative intent, and authorizes execution.
9. **Atomic Consume:** The orchestrator invokes `R-10.atomic_consume_action(nonce)`.
10. **R-7 Execution:** Orchestrator routes the original `AbstractEvidenceRequest` to the CEM.
11. **R-8 Response:** "Successfully received 50 units."

## 3. CONFIRMATION SEMANTICS
- **Confirmation:** Requires an explicit affirmative intent (e.g., "yes", "proceed") from the user mapped directly to the pending nonce in the active session.
- **Rejection:** Requires an explicit negative intent ("no", "cancel").
- **Unrelated Response:** If the user asks a new question ("What is the current stock?"), the pending action remains suspended (until TTL expiry) and the new query is processed normally.
- **Inference:** R-9 MUST NOT infer confirmation from ambiguous phrasing.
- **Modification:** R-9 MUST NOT modify the suspended `AbstractEvidenceRequest`. If the user says "Actually, make it 40 units", this constitutes a rejection of the suspended request and the initiation of a completely new R-1→R-6 flow.
- **Execution:** Confirmation resumes the *exact* suspended request natively.

## 4. ACTION SAFETY
- R-9 interacts with R-10 exclusively via the `MemoryProvider` interface.
- **Expired/Rejected actions** cannot execute because they will fail retrieval or status checks.
- **Consumed actions** cannot execute again because `atomic_consume_action()` enforces a strict lock/state change, returning `False` on subsequent attempts.
- **Concurrent confirmations** (e.g., user double-clicks "Yes") are mitigated because only the first atomic consumption succeeds; the second receives `False` and halts.
- **Bypassing R-7:** R-9 cannot execute actions itself. It simply yields the authorized `AbstractEvidenceRequest` back to the `RabtaOrchestrator`, which safely delegates to R-7.

## 5. MULTI-TURN CONTEXT
R-9 obtains multi-turn context via the orchestrator. The orchestrator loads `ConversationTurn` history from R-10 and passes it to the Intelligence Domain.
- R-9 may read the active `SuspendedExecutionState` to determine if a confirmation is expected.
- R-9 MUST NOT treat memory as authoritative business truth (e.g., it cannot check memory to see if an item is in stock).
- **Isolation:** Orchestrator enforces strict `tenant_id`, `user_id`, and `session_id` isolation when querying R-10, physically preventing R-9 from seeing cross-tenant/cross-user suspended actions.

## 6. PROACTIVE RECOMMENDATIONS
- **Generation:** R-9 can generate recommendations by evaluating the `BusinessEvidenceResponse` returned by R-7 (e.g., querying stock returns 5 units; R-9 attaches a structured recommendation to reorder).
- **Execution:** Recommendations CANNOT directly execute actions. They must be presented to the user, effectively acting as pre-populated `AbstractEvidenceRequest`s that immediately enter the R-10 Suspended state awaiting confirmation.
- **Initiation:** R-9 operates purely reactively within a user-initiated conversational turn. It cannot autonomously wake up and send recommendations without user input.

## 7. R-6 / R-9 INTERACTION
- **R-6 (Bounded Refinement)** handles capability mismatches, missing required parameters, and ambiguous entity resolution. It loops until the request is structurally valid.
- **R-9 (Decision)** takes over *only after* R-6 produces a structurally valid `AbstractEvidenceRequest`. R-9 decides if this valid request is *safe* to execute immediately or requires confirmation.

## 8. R-8 / R-9 INTERACTION
R-9 MUST NOT produce conversational text. 
R-9 produces structured cognitive state (e.g., `ConfirmationRequired(request)`, `ActionConfirmed(nonce)`). 
R-8 interprets this structured state and translates it into the final natural language response presented to the user.

## 9. R-10 / R-9 CONTRACT GAPS
The existing R-10 contracts (`SuspendedExecutionState`, `SuspendedActionStatus`, `ConversationTurn`) and the extended `MemoryProvider` interface (with `atomic_consume_action`) are structurally complete and sufficient for R-9. There are no genuine architectural gaps prohibiting R-9 implementation.

## 10. MINIMUM R-9 IMPLEMENTATION SCOPE
- **A. Multi-turn Decisions & B. Pre-execution Confirmations:**
  - Update `RabtaOrchestrator` to invoke R-9 logic before calling R-7 on mutative requests, allowing suspension via R-10.
  - Implement R-9 logic to check for active suspensions during R-1/R-2 and process affirmative/negative intents into consumption/rejection.
- **C. Proactive Recommendations:**
  - Implement R-9 logic post-R-7 to analyze evidence and optionally yield a `Recommendation` payload to R-8.
- **Production Files:** `RabtaOrchestrator`, relevant Intelligence Domain logic (e.g., `InventoryIntelligenceOrchestrator`).
- **Untouched:** R-4, R-5, R-6, R-7, and R-10 physical adapter logic must remain untouched.

## 11. CERTIFICATION CRITERIA
R-9 will be certified when:
1. Destructive actions consistently trigger suspension and wait for explicit confirmation.
2. Atomic consumption is mathematically proven via tests to prevent duplicate execution of the same nonce.
3. Rejections and unrelated queries do not accidentally trigger suspended actions.
4. Recommendations are safely structured as pending actions requiring confirmation.
5. Zero business logic or text generation leaks into R-9.

---

## Findings
R-9 is the cognitive safety valve of the RABTA framework. It cleanly separates the structural validity of a request (R-6) from the operational safety of executing it. The prerequisites (R-10 Memory) are fully in place to support this.

## R-9 Ownership Boundary
R-9 exclusively owns the decision to suspend, resume, or recommend actions. It owns no physical execution and no conversational text generation.

## R-6/R-8/R-10 Boundary Decision
- **R-6:** Resolves structural ambiguity.
- **R-9:** Determines operational safety (confirmation) and proactive next steps.
- **R-10:** Persists the state securely.
- **R-8:** Translates the outcome into human dialogue.

## Minimum Required Implementation
Integrate R-9 suspension and confirmation logic into the `RabtaOrchestrator` and Intelligence Domain. Ensure R-8 can render confirmation prompts.

## Certification Criteria
Strict adherence to execute-once semantics (via R-10 atomic consumption) and prevention of unintentional execution.

## Exact Next Implementation Workspace and Step
**Workspace:** AaramBrain
**Step:** Define the R-9 structured contracts (e.g., `ConfirmationRequired`, `Recommendation`) in the shared contracts library and implement the core R-9 interception logic in `RabtaOrchestrator`.
