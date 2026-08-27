# Phase 9 Readiness Report

## A. AUTHORITATIVE PHASE 9 DEFINITION
- **Official Name:** Ecosystem Communication & Governance
- **Objective:** Manage inbound/outbound event boundaries and security.
- **Scope:** Implement generic intake endpoints and outbound dispatchers enforcing strict schema/security guardrails. Physical event-bus technology is deferred.
- **Inputs:** Raw inbound payloads from external webhooks/events.
- **Outputs:** Governed outbound event payloads (e.g., serialized `ActionRequest` broadcasts).
- **Required Components:** Inbound Receivers, Outbound Dispatchers, Security/Validation Guardrails.
- **Files to Create:** `src/event_bus/*.py`, `src/security/*.py`, and corresponding tests.
- **Files to Modify:** None (other than tracking logs).
- **Files that must remain untouched:** Intelligence Domain reasoning loops, Brain Core contracts, physical adapters.
- **Dependencies on Phase 8:** Depends on the stable reasoning loops and `ActionRequest` boundaries.
- **Prohibited Work:** Modifying intelligence loops, coupling to physical transports (e.g., Kafka, FastAPI), or executing Phase 10 (production hardening, chaos testing).
- **Testing Requirements:** E2E security boundary tests verifying malicious/malformed payloads are rejected.
- **Exit/Certification Criteria:** Complete isolation between Intelligence Domains and external networks via governed API boundaries.
- **Relationship to Phase 10:** Phase 9 builds the logical boundary logic. Phase 10 will wrap this logic in production-hardened topologies (latency profiling, Docker networking, chaos testing).

## B. CURRENT BASELINE AFTER CERTIFIED PHASE 8
- Brain Core possesses stateful, fully-orchestrated intelligence domains capable of deterministic reasoning.
- Brain Core outputs highly governed `ActionRequest` objects.
- **Gap:** The intelligence domains are currently invoked directly via Python method calls in tests. There is no governed intake pipeline to accept, validate, and sanitize external JSON payloads (e.g., from an external webhook) before invoking the domains, nor is there a generic dispatcher to emit the `ActionRequest`.

## C. GAP ANALYSIS
The intelligence domains are functionally complete but lack a secure "front door" (intake validation) and a standardized "back door" (event dispatch). Without these, external operational systems cannot safely trigger Brain Core, and Brain Core cannot safely communicate outcomes.

## D. EXACT IMPLEMENTATION WORK REQUIRED
1. Implement a Security module (`src/security/validator.py`) to validate inbound schema payloads, enforce size limits, and block malformed structural data.
2. Implement an Inbound Receiver (`src/event_bus/receiver.py`) that acts as the entrypoint for raw events, applies security validation, and routes to the appropriate Intelligence Domain (NDR or Customer Query).
3. Implement an Outbound Dispatcher (`src/event_bus/dispatcher.py`) that receives an `ActionRequest` and safely serializes it for ecosystem broadcast.
4. Write comprehensive boundary tests ensuring isolation.

## E. FILE-LEVEL CREATE/MODIFY/KEEP MATRIX
**Create:**
- `src/event_bus/__init__.py`
- `src/event_bus/receiver.py`
- `src/event_bus/dispatcher.py`
- `src/security/__init__.py`
- `src/security/validator.py`
- `tests/event_bus/test_receiver.py`
- `tests/event_bus/test_dispatcher.py`
- `tests/security/test_validator.py`

**Modify:**
- `docs/10-implementation-plan/engineering-log.md`
- `docs/10-implementation-plan/implementation-backlog.md`

**Keep Untouched:**
- `src/intelligence_domains/*`
- `src/brain_core/*`
- `src/business_adapters/*`
- `src/infrastructure/*`
- All other existing tests.

## F. CONTRACTS THAT MUST NOT CHANGE
- `ActionRequest` and `ActionResponse` (`src/brain_core/action_engine/contracts.py`).
- Brain Core Context Definitions (`src/shared/context_contracts/`).
- Intelligence Domain Orchestrator signatures (`handle_query`, `orchestrate_resolution`).

## G. TEST STRATEGY
- **Security Tests:** Inject massive strings, malformed JSON, and unknown event types into the Inbound Receiver. Verify the Security validator rejects them before they reach the orchestrators.
- **Dispatcher Tests:** Inject a mocked `ActionRequest` into the Outbound Dispatcher and verify strict, governed JSON emission.

## H. PHASE 9 → PHASE 10 BOUNDARY
Phase 9 constructs the logical pipeline (Validator -> Receiver -> Orchestrator -> Dispatcher). Phase 10 will deal with deploying these logical pipelines into the physical network, implementing token budgets, latency profiling, and chaos engineering.

## I. RISKS / ARCHITECTURAL CONFLICTS
- **Risk:** Implementing a full web framework (e.g., FastAPI, Flask) and tightly coupling it to the Receiver. 
- **Mitigation:** The receiver must be a pure async Python boundary that accepts raw strings/dicts, agnostic to whether it was received via REST, gRPC, or AMQP.

## J. PHASE 9 EXIT CRITERIA
Complete logical isolation demonstrated through boundary tests: No invalid external payload can reach the Intelligence Domains, and all outputs are properly formatted for governed dispatch.

## K. RECOMMENDED IMPLEMENTATION ORDER
1. Build `src/security/validator.py`.
2. Build `src/event_bus/dispatcher.py`.
3. Build `src/event_bus/receiver.py`.
4. Create test suites for all three components.
5. Execute validation checks.

---

## EXPLICIT QUESTIONS ANSWERED

1. **Which AG work/session should perform each Phase 9 activity?**
   This current AG session (upon authorization).
2. **What new files will be created?**
   `src/event_bus/receiver.py`, `src/event_bus/dispatcher.py`, `src/security/validator.py`, and their corresponding test files.
3. **What existing files will be modified?**
   None, except for documentation/tracking files (`engineering-log.md`, `implementation-backlog.md`).
4. **Which files must remain untouched?**
   All Phase 1-8 architecture files (Intelligence domains, adapters, context schemas, interfaces).
5. **What documentation/status files must be updated?**
   `engineering-log.md` and `implementation-backlog.md`.
6. **Who updates the phase status?**
   The AI Agent.
7. **What exact verification commands will be required?**
   `PYTHONPATH=. pytest tests/event_bus tests/security -v` followed by `PYTHONPATH=. pytest -v`.
8. **What must be committed to Git at the end of Phase 9?**
   All new `src/event_bus`, `src/security`, and test files, alongside the documentation updates.
9. **What conditions must be satisfied before Phase 10 is unlocked?**
   100% Phase 9 tests passing, successful boundary security validation, and explicit Git commit marking Phase 9 completion.

---

PHASE 9:
READY TO IMPLEMENT
