# Catalog ID Data Schema & Logical Persistence

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/06-catalog-id-data-schema.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 1.0
**Last Updated:** September 1, 2026

---

## 1. Executive Summary & Logical Boundary

This document defines the **logical persistence boundary** for Catalog ID. 

**CRITICAL INVARIANT:** Catalog ID does not own canonical catalog truth. It must never store a shadow copy of the Product or SKU masters. 

### Technology Agnosticism
This specification defines *what* categories of state Catalog ID is permitted to persist logically. It explicitly **does not mandate** specific physical implementation technologies (e.g., PostgreSQL, Vector Databases, embeddings stores, Qwen Coder, RABTA, or specific ML infrastructure). 

> **OPEN GAP / DECISION REQUIRED:** The exact physical storage engines and ML infrastructure to support this logical schema must be selected and documented during the physical implementation phase, ensuring they do not violate the boundaries established herein.

---

## 2. Permitted Logical State Categories

Catalog ID is authorized to own and persist intelligence-process state required for intake, reasoning, human review, auditability, and re-processing. 

### 2.1 Intake & Process State (`IntakeSession`)
- **Purpose:** To maintain the state of an ongoing interaction (conversational thread, bulk upload progress) before it results in a definitive Catalog BS command.
- **Logical Data Elements:**
  - Session Identifier
  - Raw Input Payloads (Text, Image URIs)
  - Current Pipeline Stage (e.g., Extracting, Scoring, Awaiting Human Review)
  - Expiration / TTL constraints (working state should not persist indefinitely).

### 2.2 Candidate Assessments & Scoring (`MatchAssessment`)
- **Purpose:** To temporarily hold the cognitive reasoning outputs and similarity scores used to reach a resolution decision.
- **Logical Data Elements:**
  - Proposed Candidate Attributes
  - Discovered Catalog BS Identifiers (`internal_id`s evaluated)
  - Similarity / Confidence Scores
  - Disambiguation rationale.

### 2.3 Review & Audit State (`ResolutionDecision`)
- **Purpose:** To record *why* a particular cognitive decision was made, supporting human audits and AI continuous improvement.
- **Logical Data Elements:**
  - Final Decision Class (e.g., Strong Candidate vs Ambiguous)
  - Resulting Command Payload (the JSON sent to Catalog BS)
  - Human Intervention Logs (who approved the ambiguous candidate and when).

---

## 3. Explicit Prohibitions (What Catalog ID Must NEVER Persist)

1. **Canonical Product Master:** Catalog ID must not persist authoritative product attributes (Pricing, Packaging Dimensions, HSN codes) outside the context of a temporary `Candidate` session.
2. **Canonical SKU Master:** Catalog ID must not attempt to persist authoritative `sku_id` assignment ledgers. Catalog BS owns `catalog_sku_id_reservations`.
3. **Channel Mapping State:** Catalog ID must not persist mappings between ShopDeck tokens and Aaram SKUs. This is owned by `catalog_channel_mappings` in Catalog BS.
