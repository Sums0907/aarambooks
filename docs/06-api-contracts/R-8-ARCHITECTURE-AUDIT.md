# R-8 Architecture Audit

## 1. R-8 PURPOSE

**Exact Responsibility:**
R-8 (Interpretation) owns the translation of the abstract, structured `BusinessEvidenceResponse` (returned by R-6/R-7 execution) into the final conversational response for the user. It determines what information the user needs to see, what clarification questions need to be asked, and how to format the data (e.g., text, UI components).

**What R-8 Owns:**
- Natural language generation based on CEM outcomes.
- Formatting clarification requests for the user (e.g., presenting multiple candidates to choose from).
- Explaining business-rule rejections conversationally.

**What Must Remain Outside R-8:**
- Business state mutation or payload construction (R-7).
- Bounded refinement loops or automated retries (R-6).
- Entity resolution or business identifier generation (R-5).
- Direct database access.

## 2. INPUT CONTRACT

R-8 receives the execution outcome from R-6/R-7 via the `RabtaOrchestrator`.

**Authoritative Contract:** `BusinessEvidenceResponse` (defined in `src/shared/evidence_request_contracts.py`).

**Authoritative Fields:**
- `status: BusinessRealityStatus`
- `evidence_data: Optional[Dict[str, Any]]`
- `resolved_candidates: Dict[str, List[CandidateEntity]]`
- `capabilities_discovered: List[str]`
- `execution_limitations: List[ExecutionLimitation]`

## 3. OUTPUT CONTRACT

**Exact Object/Result Required:**
R-8 must produce a structured conversational response containing the final text, clarification prompts, and UI render directives.

**Existing Contract Support:**
Currently, `IntelligenceDomainProvider.interpret_evidence` in `src/shared/rabta_interfaces.py` returns `Any`. There is **no existing strict contract** (e.g., `ConversationalResponse`) defined for R-8 output. This is a gap that must be filled.

## 4. EXECUTION_LIMITATION HANDLING

Ownership of resolution for these cases belongs to the **User** (via R-8 asking them), not the AI autonomously guessing.

- **Missing action parameters:** R-8 reads the `execution_limitations` and generates a conversational prompt asking the user to provide the specific missing value.
- **Invalid parameters:** R-8 generates a prompt explaining why the value was invalid and asks for a correction.
- **Ambiguous entities:** R-8 receives `MULTIPLE_CANDIDATES` with `resolved_candidates`. R-8 presents these options to the user to choose from.
- **Ambiguous capabilities:** R-8 asks the user to clarify their intent.
- **Business-rule rejection:** R-8 reads the `EXECUTION_LIMITATION` reason (e.g., "insufficient stock") and informs the user that the action was rejected.
- **Technical/system failure:** As established in the R-6/R-7 boundary audit, system failures bubble up as raw exceptions and are caught by `RabtaOrchestrator`, which returns `"CEM Execution Error: {str(e)}"`. R-8 is bypassed entirely for system failures.

## 5. R-7 BOUNDARY

R-8 is strictly read-only regarding business state. It receives a read-only `BusinessEvidenceResponse` and formats it. R-8 cannot modify the `AbstractEvidenceRequest`, nor can it invoke the CEM directly. It relies entirely on the orchestrator's handoff. Therefore, R-8 does not duplicate any R-7 execution responsibilities.

## 6. USER CLARIFICATION BOUNDARY

R-8 produces a **clarification request** when:
- `BusinessRealityStatus` is `MULTIPLE_CANDIDATES`.
- `BusinessRealityStatus` is `EXECUTION_LIMITATION` involving missing or invalid parameters.

R-8 produces a **normal business response** when:
- `BusinessRealityStatus` is `EVIDENCE_AVAILABLE`, `ENTITY_RESOLVED`, or `CAPABILITY_AVAILABLE` (successful execution).

R-8 produces a **technical failure** when:
- It doesn't. System failures are caught by the orchestrator before reaching R-8.

## 7. ARCHITECTURAL GAPS

**Genuine Blocker:** The `interpret_evidence` method on `IntelligenceDomainProvider` returns `Any`. To safely connect R-8 to a user interface or API gateway, a formalized `ConversationalResponse` contract must be introduced in `src/shared/conversational_contracts.py` so the orchestrator can depend on a strongly-typed output.

## 8. IMPLEMENTATION PLAN

- **Exact Workspace:** AaramBrain
- **Exact Production Files Likely to Change:** 
  - `src/shared/rabta_interfaces.py` (Update `interpret_evidence` signature)
  - `src/shared/conversational_contracts.py` (Introduce `ConversationalResponse`)
- **Exact New Files Likely Required:** 
  - `src/intelligence_domains/inventory_intelligence/interpreter.py` (Implementation of the R-8 interpreter for Inventory ID)
- **Exact Tests Required:** 
  - Unit tests mapping `BusinessEvidenceResponse` (Success, Multiple Candidates, Execution Limitation) into `ConversationalResponse`.

---

- **Findings:** R-8's responsibilities are clearly bounded as the translation layer from structured CEM output to conversational output. R-8 is appropriately isolated from execution and state mutation.
- **R-8 Ownership Boundary:** R-8 owns natural language generation and clarification prompt formatting. It does not own execution, retry logic, or entity resolution.
- **Input/Output Contract Decision:** Input is `BusinessEvidenceResponse`. Output is currently `Any` and must be formalized into `ConversationalResponse`.
- **Architectural Blockers:** Missing `ConversationalResponse` contract.
- **Required Implementation Steps:** Define the output contract, implement the ID-specific interpreter, and update the orchestrator interface.
- **R-8 Certification Criteria:** R-8 can be certified when it correctly maps all `BusinessRealityStatus` enum values to safe, user-facing conversational constructs without attempting autonomous execution retries.
- **Exact Next AG Workspace and Implementation Step:** 
  - Workspace: `AaramBrain`
  - Step: Formalize the `ConversationalResponse` contract in `src/shared/conversational_contracts.py` and update `IntelligenceDomainProvider.interpret_evidence` to return it.
