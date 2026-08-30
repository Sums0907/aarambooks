# R-6 / R-7 BOUNDARY AUDIT

## 1. R-6 / R-7 EXECUTION_LIMITATION OWNERSHIP

### Trace of EXECUTION_LIMITATION
When R-7 returns `EXECUTION_LIMITATION` (due to missing parameters, invalid parameters, business-rule rejection, etc.), the `RabtaOrchestrator` receives the `BusinessEvidenceResponse`.
Inside the R-6 Bounded Refinement loop (lines 87-93 of `rabta_orchestrator.py`), Brain Core checks if `status == BusinessRealityStatus.MULTIPLE_CANDIDATES`. Since the status is `EXECUTION_LIMITATION`, the condition evaluates to `False`. 
Brain Core **terminates the R-6 loop immediately**. It does **not** refine. It does **not** retry CEM.
The orchestrator then passes the response to R-8, which interprets the limitation and asks the user for clarification.

### Architectural Correctness
This behavior is **architecturally correct**. Brain Core lacks the domain knowledge to autonomously invent missing action parameters, override business-rule rejections, or resolve capability ambiguities. Terminating the automated loop and handing off to R-8 (User Clarification) is the only mathematically safe behavior. 

**Smallest architectural correction required:** None. The current loop structure in `rabta_orchestrator.py` correctly terminates on `EXECUTION_LIMITATION`.

## 2. R-6 BOUNDARY

Based on the authoritative orchestrator implementation, R-6 is intended to handle **ONLY** semantic/entity ambiguity (i.e., `MULTIPLE_CANDIDATES`).

R-6 is **NOT** intended to handle:
- Missing action parameters (falls through to R-8)
- Invalid action parameters (falls through to R-8)
- Capability ambiguity (handled at R-4 routing, or falls through to R-8)
- Business-rule failures (falls through to R-8)

## 3. EXCEPTION MASKING

If the upcoming R-7 payload construction adapters use broad exception handling (e.g., `try... except Exception: return EXECUTION_LIMITATION`), a critical architectural failure will occur.

**The Boundary:**
Broad exception handling would incorrectly translate authorization errors, database connection drops, programming errors (NullPointer, etc.), and unexpected infrastructure failures into conversational limitations. The AI would ask the user conversational questions to resolve a database outage.

**Exact Boundary Distinction:**
- **Conversational `EXECUTION_LIMITATION`:** Must strictly be reserved for domain-level `ValidationException` (e.g., "Quantity must be > 0", "Insufficient stock") or missing NormalizedParameters.
- **System Failures:** Authorization errors, `OperationalError`, and generic unhandled `Exception`s **MUST NOT** be caught by R-7 to return `EXECUTION_LIMITATION`. They must be allowed to bubble up, triggering a system-level failure (HTTP 500) so the orchestrator returns a technical "CEM Execution Error" rather than a conversational clarification.

## 4. RETRY SAFETY

Can an `EXECUTION_LIMITATION` retry accidentally execute the same state-changing action twice?
- **R-6 Automated Retry:** Impossible. R-6 structurally breaks the loop on `EXECUTION_LIMITATION` and never retries.
- **User-Initiated Retry:** If the user provides the missing parameter in a subsequent turn, a new `AbstractEvidenceRequest` is dispatched. If the domain service failed halfway through the first attempt without rolling back its database transaction, the second attempt could cause double-execution (e.g., orphaned records).

**Architectural Enforcement:**
Because R-7 simply acts as an adapter, **existing Inventory domain services remain the absolute authority for transaction boundaries**. R-7 must not manage `db.commit()` or `db.rollback()`. If the domain service fails, it must automatically rollback its own transaction, ensuring that R-7 retries are perfectly safe.

## 5. FINAL DECISION

**Findings:** 
The R-6 boundaries are correctly constrained. R-6 properly avoids guessing missing execution parameters. The primary remaining risk is Exception Masking inside the pending R-7 adapters.

**Boundary Decision:**
R-7 must strictly segregate Domain Validation Exceptions (map to `EXECUTION_LIMITATION`) from System/Infrastructure Exceptions (must bubble up).

**Required Changes:**
When implementing the R-7 adapters, ensure `try/except` blocks specifically target known Domain Validation errors, not generic `Exception`.

**Certification Impact:**
R-7 CONDITIONAL CERTIFICATION REMAINS. 

**Exact Conditions that must be satisfied for Final Certification:**
1. R-7 adapters must exclusively catch specific Domain/Validation exceptions for mapping to `EXECUTION_LIMITATION`.
2. All generic `Exception`s must bubble up as system errors.
3. R-7 adapters must demonstrably rely on the authoritative domain services for transaction management, performing zero direct session commits.

**Exact next implementation workspace and step:**
Workspace: Aaram_Inventory (`/Users/sumatidhingra/Documents/AaramBooks/Aaram_Inventory/`)
Step: Implement the R-7 Payload Construction Adapters (starting with Goods Receipt) ensuring strict compliance with the Exception Masking and Transaction boundary rules defined above.
