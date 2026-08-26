# Engineering Log

## Purpose

Track significant implementation, testing, integration, deployment, and debugging events so that failures, root causes, fixes, and validation results are not lost between sessions.

## Rules

- Record significant engineering failures and discoveries.
- Record root cause, not just symptoms.
- Record the final fix and validation.
- Keep resolved incidents permanently.
- Reference related previous incidents where applicable.
- Never record secrets, credentials, tokens, or unnecessary PII.
- Do not use this file as a raw application log.
- Runtime logs remain the responsibility of the application/container logging system.

---

## Required Entry Fields

- **Incident ID:** Unique identifier (e.g., INC-YYYYMMDD-001)
- **Date:** YYYY-MM-DD
- **Milestone:** Associated project milestone
- **Component:** System component involved
- **Problem:** Brief description of the issue
- **Error / Symptom:** What was observed (stack trace, error code)
- **Root Cause:** The fundamental reason for the failure
- **Fix:** The actions taken to resolve it
- **Files Changed:** List of modified files
- **Validation:** How the fix was verified
- **Status:** OPEN / RESOLVED
- **Related Incident / Decision:** Links to ADRs or previous incidents

---

## Log Entries

*(Copy the template below to create new entries)*

### Incident ID: [ID-YYYYMMDD-HHMM]
- **Date:** 
- **Milestone:** 
- **Component:** 
- **Problem:** 
- **Error / Symptom:** 
- **Root Cause:** 
- **Fix:** 
- **Files Changed:** 
- **Validation:** 
### Incident ID: INC-20260824-001
- **Date:** 2026-08-24
- **Milestone:** 1.1 Context Engine Registry
- **Component:** Provider Registry (Context Engine)
- **Problem:** Domain Leakage into Infrastructure & Incomplete Capability Resolution
- **Error / Symptom:** The generic ProviderRegistry infrastructure hardcoded Aaram-specific domain concepts (ProviderCapability Enum). Additionally, ContextAssembler failed to resolve internal authorities (Inventory, Fulfillment, Security) relying strictly on external source_system hints.
- **Root Cause:** Rushed implementation of the DI mechanism placed capability definition inside the registry itself, causing an inward dependency violation for Adapters that must register against those capabilities.
- **Fix:** Relocated `ProviderCapability` to `src/shared/context_contracts/capability.py`. Updated ContextAssembler to resolve internal systems (AaramIdentity, AaramInventory, AaramPacking) using fixed internal SourceSystem Enums rather than dynamic HTTP request hints.
- **Files Changed:** `registry.py`, `assembler.py`, `shared/context_contracts/capability.py`, `context-contract-architecture.md`, `provider-registry-architecture.md`
- **Validation:** Tests verified duplicate registration fails, missing fails, dynamic customer/order resolution works, and fixed internal resolution works.
- **Status:** RESOLVED
- **Related Incident / Decision:** Provider Registry Architecture (docs/02-brain-core/provider-registry-architecture.md)

---

### Incident ID: INC-20260824-002
- **Date:** 2026-08-24
- **Milestone:** 1.1 Context Engine Registry
- **Component:** Application Root / Configuration
- **Problem:** Ambiguity in Provider Construction and Configuration lifecycle.
- **Error / Symptom:** Unclear boundary over where providers should be instantiated and how secrets/credentials should be passed, raising the risk of hardcoded secrets or lazy-loading runtime errors in production.
- **Root Cause:** The generic ProviderRegistry decoupled Brain Core from adapters, but did not solve who was responsible for configuring the adapters.
- **Fix:** Architected the Application Composition Root pattern. Eager, fail-fast construction forces validation at startup. Centralized all wiring into `main.py` using validated Pydantic settings.
- **Files Changed:** `docs/01-architecture/application-composition-boundary.md`
- **Validation:** Architecture documented and cross-referenced with Registry architecture.
- **Status:** RESOLVED
- **Related Incident / Decision:** Provider Registry Architecture (docs/02-brain-core/provider-registry-architecture.md)

---

### Incident ID: INC-20260824-003
- **Date:** 2026-08-24
- **Milestone:** 1.1 Context Engine Registry
- **Component:** Data Governance / Git
- **Problem:** Absence of protection mechanisms against committing raw operational data containing PII.
- **Error / Symptom:** Raw ShopDeck customer CSV extracts carrying real names and phone numbers could be accidentally staged and pushed, violating data privacy boundaries.
- **Root Cause:** No explicit governance or automated Git blocks existed for the `sample-data/**/raw/` directories.
- **Fix:** Formalized the Raw Data Protection Standard in the Engineering Foundation. Updated `.gitignore` to explicitly block `sample-data/**/raw/`. Created a Git `pre-commit` hook to automatically reject commits containing raw data.
- **Files Changed:** `.gitignore`, `docs/10-implementation-plan/engineering-foundation-standard.md`, `sample-data/shopdeck/README.md`, `.git/hooks/pre-commit`
- **Validation:** Ensured local raw data (`customers-export.csv`) is untracked and blocked by Git hooks.
- **Status:** RESOLVED
- **Related Incident / Decision:** Engineering Foundation Standard (docs/10-implementation-plan/engineering-foundation-standard.md)

---

### Incident ID: INC-20260824-004
- **Date:** 2026-08-24
- **Milestone:** 1.1 Context Engine Registry
- **Component:** ShopDeck Customer Provider
- **Problem:** Missing authoritative identity fields in ShopDeck data samples.
- **Error / Symptom:** The raw `customers-export.csv` provides only `"Name"` and `"Phone No"`. Without an explicit system primary key (like an `id` or `uuid`), mapping an authoritative `customer_reference` is impossible. 
- **Root Cause:** A CSV export is a flattened reporting view, not equivalent to the true ShopDeck REST API payload structure.
- **Fix:** Formally blocked the implementation of the ShopDeck Customer Provider. Asserted that `"Phone No"` must **NOT** be assumed to be the system's `customer_reference`. `customer_reference` remains generically defined as the provider-authoritative customer reference.
- **Files Changed:** None (implementation intentionally blocked).
- **Validation:** N/A
- **Status:** BLOCKED
- **Related Incident / Decision:** N/A (Awaiting official ShopDeck API documentation or a sanitized raw JSON API response).

---
