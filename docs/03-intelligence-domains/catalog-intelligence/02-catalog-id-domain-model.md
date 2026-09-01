# Catalog ID Domain Model

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/02-catalog-id-domain-model.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.1
**Last Updated:** September 1, 2026

---

## 1. Executive Summary & Purpose

This document establishes the **Cognitive Domain Model** for Catalog ID. It defines the conceptual entities used during the intelligence workflow.

**CRITICAL INVARIANT:** These cognitive concepts (`IntakeSession`, `Candidate`, `MatchAssessment`) are explicitly working states. They must **never** become shadow versions of canonical Catalog BS `Product`, `SKU`, or lifecycle states.

---

## 2. Cognitive Working State Entities

### 2.1 `IntakeSession`
- **Definition:** The context of a single cognitive workflow.
- **Role:** Tracks progression, raw inputs, and the resolution status.

### 2.2 `CandidateProduct` / `CandidateSKU`
- **Definition:** The proposed structure of a product or SKU.
- **Role:** Holds attributes before they are submitted to Catalog BS. It is a hypothesis, not a fact.

### 2.3 `MatchAssessment`
- **Definition:** An evaluation of how well a candidate aligns with an existing Catalog BS entity.
- **Role:** Stores comparison signals, evidence conflicts, and the `SimilarityScore`.

### 2.4 `ResolutionDecision`
- **Definition:** The final cognitive conclusion (e.g., "Propose new Product", "Propose attachment to existing `internal_id`").

---

## 3. Data Provenance Semantics

Every attribute/state within a candidate must have clear provenance semantics to prevent accidental mixing of extracted facts, inferred attributes, and canonical Catalog BS truth.

| Provenance Tag | Definition | Concept Usage |
|---|---|---|
| **`USER_SUPPLIED`** | Explicitly provided by the human operator. | User typed: `"Selling price is 1500"` |
| **`EXTRACTED`** | Derived deterministically from structured/semi-structured input. | Extracted `100% Cotton` from a vendor CSV label. |
| **`INFERRED`** | Probabilistically guessed by the cognitive model. | Guessed `size_type = size` based on dimensions. **Must never be implied as canonical truth.** |
| **`DISCOVERED_CANONICAL`**| A confirmed fact retrieved from Catalog BS public read contracts (`vw_catalog_master`). | Retrieved `internal_id` for an existing product. |
| **`PROPOSED`** | A new identifier generated via Catalog ID heuristics to be sent for validation. | Generated candidate `sku_id = 126BS-RED`. |

**Boundary Rule:** It must be conceptually impossible to confuse a `PROPOSED`, `INFERRED`, or `USER_SUPPLIED` value with a `DISCOVERED_CANONICAL` value. Probabilistic similarity produces a `Candidate`, not canonical identity.
