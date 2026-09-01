# Catalog ID Data Schema & Logical Persistence

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/06-catalog-id-data-schema.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.0
**Last Updated:** September 1, 2026

---

## 1. Executive Summary & Logical Boundary

This document defines the **logical persistence boundary** for Catalog ID. 

**CRITICAL INVARIANT:** Catalog ID does not own canonical catalog truth. It must never store a shadow copy of the Product or SKU masters. 

### Technology Agnosticism
This specification explicitly **does not mandate** specific physical implementation technologies (e.g., PostgreSQL, Vector Databases, embeddings stores, Qwen Coder, RABTA). It defines *what* must be stored logically, not *how*.

---

## 2. Logical Persistence Requirements

Catalog ID requires persistence capabilities to maintain intelligence-process state. Any underlying storage technology must support the following logical requirements:

### 2.1 Session Lifecycle & Resumability
- **Requirement:** `IntakeSession` state must be persistable to allow for suspension (e.g., awaiting human review) and resumability across network boundaries or asynchronous worker executions.
- **Expiration:** Sessions must have a defined TTL/expiration. Abandoned drafts should not persist indefinitely.

### 2.2 Candidate Provenance & Traceability
- **Requirement:** Every attribute in a `CandidateProduct` must retain its provenance tag (`USER_SUPPLIED`, `EXTRACTED`, `INFERRED`, `DISCOVERED_CANONICAL`, `PROPOSED`).
- **Reasoning Trace:** The `MatchAssessment` must store a reasoning trace—an audit log of *why* a particular similarity score was assigned or why an ambiguous state was triggered.

### 2.3 Linkage to Catalog BS Results
- **Requirement:** Once a command is dispatched to Catalog BS, the resulting `idempotency_key` and final status (`SUCCESS` or `REJECTED`) must be linked back to the `IntakeSession`.
- **Re-processing:** If a rejection occurs, the session must be capable of resuming, altering the `PROPOSED` identifiers (e.g., executing the next bounded retry), and re-dispatching.

---

## 3. Explicit Prohibitions

1. **No Canonical Storage:** Catalog ID must not persist authoritative product attributes, pricing, or historical reservation ledgers outside the strict bounds of an active `IntakeSession` or an archived audit log.
2. **No Second Master:** Do not persist a shadow Product/SKU master under the guise of an "intelligence cache". If current catalog truth is needed, it must be discovered fresh via Catalog BS read contracts.
