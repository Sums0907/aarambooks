# Catalog ID Data Schema & Logical Persistence

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/06-catalog-id-data-schema.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.1
**Last Updated:** September 1, 2026

---

## 1. Executive Summary & Logical Boundary

This document defines the **logical persistence boundary** for Catalog ID. 

**CRITICAL INVARIANT:** Catalog ID does not own canonical catalog truth. It must never reproduce a shadow copy of the Product or SKU masters. 

### Technology Agnosticism
This specification explicitly **does not mandate** PostgreSQL tables, vector databases, embedding infrastructure, LLM vendors, specific model names, or storage engines unless explicitly supported by authoritative project documentation. It defines *what* must be stored logically, not *how*.

---

## 2. Logical Persistence Requirements

Catalog ID requires persistence capabilities solely to maintain intelligence-process state. Every field persisted logically must represent one of the following:

- User input (raw strings, image URIs)
- Extracted information (parsed attributes)
- Inferred information (probabilistic guesses)
- Discovered canonical information (retrieved `internal_id` anchors for attachment)
- Proposed output (candidate identifiers before submission)
- Workflow state (session status, human-review blocks)
- Reasoning/audit state (similarity scores, AI rationale logs)

### 2.1 Session Lifecycle & Resumability
- **Logical State:** `IntakeSession`.
- **Requirement:** Must support suspension (e.g., awaiting human review) and resumability. 
- **Expiration:** Must have defined retention/expiration boundaries to clear abandoned cognitive drafts.

### 2.2 Candidate Provenance & Traceability
- **Logical State:** `MatchAssessment`, `Candidate`.
- **Requirement:** Must logically persist the provenance tag of every attribute (`USER_SUPPLIED`, `EXTRACTED`, etc.).
- **Reasoning Trace:** Must persist an audit log of *why* a particular similarity score was assigned or why an ambiguous state was triggered.

### 2.3 Command Linkage
- **Logical State:** `ResolutionDecision`.
- **Requirement:** Must logically link the generated Catalog BS `idempotency_key` and final status (`SUCCESS` or `REJECTED`) back to the originating `IntakeSession`.

---

## 3. Explicit Prohibitions

1. **No Shadow Master:** Catalog ID must not persist authoritative product attributes, pricing, dimensions, or historical reservation ledgers. Any canonical data cached within an `IntakeSession` is explicitly non-authoritative.
2. **No Implementation Commitments:** This schema must not be used to justify the premature procurement or freezing of specific ML/Vector database infrastructure.
