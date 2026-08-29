# R-8 Interpreter Design Review

## 1. INPUT

R-8 receives exactly one input from the Orchestrator: the `BusinessEvidenceResponse`.
This payload contains the following authoritative information:
- `status` (`BusinessRealityStatus`)
- `evidence_data` (Dictionary of successful execution results or retrieved data)
- `resolved_candidates` (Dictionary mapping semantic references to lists of `CandidateEntity` for disambiguation)
- `capabilities_discovered` (List of applicable capability URNs)
- `execution_limitations` (List of `ExecutionLimitation` objects detailing missing parameters or business rejections)

## 2. STATUS MAPPING

R-8 maps `BusinessRealityStatus` to `ConversationalResponseType`:
- `CAPABILITY_AVAILABLE` -> `SUCCESS`
- `CAPABILITY_UNAVAILABLE` -> `EXECUTION_LIMITATION`
- `ENTITY_RESOLVED` -> `SUCCESS`
- `MULTIPLE_CANDIDATES` -> `CLARIFICATION_REQUIRED`
- `ENTITY_NOT_FOUND` -> `EXECUTION_LIMITATION`
- `EVIDENCE_AVAILABLE` -> `SUCCESS`
- `EVIDENCE_UNAVAILABLE` -> `SUCCESS` (A valid business response indicating 0 records found)
- `PARTIAL_EVIDENCE` -> `SUCCESS`
- `EXECUTION_LIMITATION` -> `EXECUTION_LIMITATION` or `CLARIFICATION_REQUIRED` (Depends on limitation type)

## 3. EXECUTION_LIMITATION

When `BusinessEvidenceResponse` contains `execution_limitations`, R-8 applies the following logic:
- **Missing parameter:** R-8 maps to `CLARIFICATION_REQUIRED`. It extracts the `missing_parameter` name, adds it to `ConversationalResponse.missing_parameters`, and constructs a prompt: "Please provide the [parameter name]."
- **Invalid parameter:** Maps to `CLARIFICATION_REQUIRED` with a prompt asking for correction based on the limitation reason.
- **Ambiguous capability / entity:** Usually handled by `MULTIPLE_CANDIDATES`, but if returned as a limitation, it maps to `CLARIFICATION_REQUIRED`.
- **Business-rule rejection:** Maps strictly to `EXECUTION_LIMITATION`. R-8 constructs a message using the limitation `reason` (e.g., "Action rejected: Insufficient stock in warehouse").

R-8 performs **zero** execution, validation, or retries. It merely translates the factual limitation into the conversational contract.

## 4. MULTIPLE_CANDIDATES

When `status == MULTIPLE_CANDIDATES`, R-8 maps to `CLARIFICATION_REQUIRED`.
It extracts `resolved_candidates` and maps them into `ConversationalResponse.clarification_options`.
- The `business_id` is passed opaquely into the `id` field of the UI option.
- The `business_name` is passed as the display label.
- R-8 performs absolutely no entity resolution or UUID manipulation. It merely formats the provided candidates for presentation.

## 5. SUCCESS

When `status == EVIDENCE_AVAILABLE` (or successful Action execution), R-8 maps to `SUCCESS`.
R-8 inspects `evidence_data`.
- Instead of inventing facts, R-8 deterministically formats the data into a readable `message` (e.g., "Successfully received 50 units of SKU-123.").
- It may populate `render_directives` so the UI knows to render a specific component (e.g., a data table for inventory balances).

## 6. SYSTEM FAILURE

Under the current architecture (verified in the R-6/R-7 boundary audit), system failures (e.g., database connection drops, unhandled exceptions in the CEM) **do not reach R-8**. 
They are caught by `RabtaOrchestrator` which returns a hard-coded technical string (`"CEM Execution Error..."`). The current boundary is consistent and architecturally safe, preventing system errors from being treated as conversational events. No redesign is needed here.

## 7. INVENTORY-SPECIFIC VS GENERIC

- **Generic (Brain Core):** Owns the `ConversationalResponse` contract definition and the Orchestrator loop.
- **Inventory-Specific (Intelligence Domain):** Owns the actual implementation of `IntelligenceDomainProvider.interpret_evidence`. Formatting a specific inventory payload (like a BOM or Stock Balance) into readable text requires domain knowledge that Brain Core should not possess.

## 8. ORCHESTRATOR BOUNDARY

`RabtaOrchestrator` simply awaits `id_provider.interpret_evidence(evidence_response)` and returns the resulting `ConversationalResponse` directly to the caller. The orchestrator must not inspect, modify, or duplicate any interpretation logic.

## 9. LLM/NLG BOUNDARY

An LLM is **not required** for R-8 at this stage. Deterministic structured interpretation (if/else mapping of statuses and string formatting for messages) is entirely sufficient, mathematically safer, and faster. Introducing an LLM merely to format "Missing parameter: Quantity" into "Could you please tell me the quantity?" is an unnecessary dependency.

## 10. IMPLEMENTATION PLAN

- **Production Files:** Create `src/intelligence_domains/inventory_intelligence/interpreter.py` containing the `InventoryInterpreter` class.
- **Tests:** Create `tests/intelligence_domains/inventory_intelligence/test_interpreter.py` to assert correct mapping of all statuses.
- **Responsibilities:** Strictly map the 5 core scenarios (Success, Missing Param, Business Rejection, Multiple Candidates, Empty Evidence) into `ConversationalResponse`.
- **Dependencies:** Relies entirely on `BusinessEvidenceResponse` and `ConversationalResponse`.

---

- **Findings:** R-8 logic can be implemented safely using purely deterministic mapping.
- **R-8 interpreter boundary:** R-8 translates structured evidence into structured conversational UI directives without mutating state or inventing data.
- **Status mapping decision:** `MULTIPLE_CANDIDATES` and Missing Parameters map to `CLARIFICATION_REQUIRED`. Business rejections map to `EXECUTION_LIMITATION`. All evidence/action successes map to `SUCCESS`.
- **Generic vs Inventory-specific responsibility:** The interpreter implementation belongs inside the Inventory Intelligence Domain (`src/intelligence_domains/inventory_intelligence/`).
- **Architectural blockers:** None. The contract is ready.
- **Smallest implementation plan:** Create `InventoryInterpreter` and write unit tests for the mappings.
- **Certification criteria:** R-8 is certifiable when the interpreter deterministically maps all `BusinessRealityStatus` conditions correctly and safely propagates opaque business IDs for clarification.
- **Exact next AG workspace and implementation step:** 
  - Workspace: AaramBrain
  - Step: Implement `InventoryInterpreter` in `src/intelligence_domains/inventory_intelligence/interpreter.py` and integrate it into the Inventory ID provider.
