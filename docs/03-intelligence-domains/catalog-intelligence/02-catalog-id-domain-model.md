# Catalog ID Domain Model

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/02-catalog-id-domain-model.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.0
**Last Updated:** September 1, 2026

---

## 1. Executive Summary & Purpose

This document establishes the **Cognitive Domain Model** for Catalog ID. It defines the conceptual entities used during the intelligence process. 

**CRITICAL INVARIANT:** These cognitive entities represent *working state*. They are **never** canonical catalog truth and must never become a shadow Product/SKU master.

---

## 2. Cognitive Working State Entities

### 2.1 `IntakeSession`
- **Definition:** The context of a single cognitive workflow.
- **Role:** Tracks progression, raw inputs, and the resolution status.

### 2.2 `CandidateProduct` / `CandidateSKU`
- **Definition:** The proposed structure of a product or SKU.
- **Role:** Holds attributes before they are submitted. It lacks canonical anchors until resolved.

### 2.3 `MatchAssessment`
- **Definition:** An evaluation of how well a candidate aligns with an existing Catalog BS entity.
- **Role:** Stores comparison signals, evidence conflicts, and the `SimilarityScore`.

### 2.4 `ResolutionDecision`
- **Definition:** The final cognitive conclusion (e.g., "Propose new Product", "Propose attachment").

---

## 3. Candidate Data Semantics

To prevent confusing working state with canonical truth, every attribute within a `CandidateProduct` or `CandidateSKU` must be logically tagged with its provenance.

| Provenance Tag | Definition | Example |
|---|---|---|
| **`USER_SUPPLIED`** | Explicitly provided by the human operator. Highly trusted, overrides inferred values. | User typed: `"Selling price is 1500"` |
| **`EXTRACTED`** | Derived deterministically from structured/semi-structured input (e.g., OCR on a label). | Extracted `100% Cotton` from label image. |
| **`INFERRED`** | Probabilistically guessed by the ML model. Lowest trust; requires verification if overriding rules. | Guessed `size_type = size` based on dimensions. |
| **`DISCOVERED_CANONICAL`**| A confirmed fact retrieved from Catalog BS public read contracts. Immutable within Catalog ID. | Retrieved `internal_id` for `AH-BED-001`. |
| **`PROPOSED`** | A new identifier generated via Catalog ID heuristics to be sent for validation. | Generated candidate `sku_id = 126BS-RED`. |

It must be conceptually impossible to confuse a `PROPOSED` or `USER_SUPPLIED` value with a `DISCOVERED_CANONICAL` value.

---

## 4. Boundary Enforcement

- **No Shadow Identities:** Candidates do not generate their own UUIDs to act as primary keys.
- **Strict Sovereignty:** Catalog ID does not maintain synchronized copies of `Product` or `SKU` tables.
