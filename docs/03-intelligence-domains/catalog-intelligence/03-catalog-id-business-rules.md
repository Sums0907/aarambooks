# Catalog ID Business Rules & Heuristics

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/03-catalog-id-business-rules.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.1
**Last Updated:** September 1, 2026

---

## 1. Product Family Reasoning Framework

Catalog ID determines if an intake candidate represents an existing family or constitutes a new product. This reasoning evaluates similarity to generate a *proposal*; it does not create canonical identity.

**Reasoning Hierarchy:**
1. **Is canonical identity explicitly supplied?** 
   - If the user provides a direct `product_internal_id`, evaluate for direct attachment.
2. **Is there a deterministic existing-entity match?** 
   - E.g., exact barcode match mapping to a `DISCOVERED_CANONICAL` `internal_id`.
3. **Does the candidate represent the same underlying commercial design?** 
   - Are the lifestyle images, fabric, and base structure identical to an existing family?
4. **Are differences only variant-level attributes?** 
   - Are the only variations in color, size, or packaging?
5. **Does product construction/component composition remain materially the same?** 
   - (e.g., A single bedsheet vs a bedsheet + pillow cover set are typically distinct).
6. **Is the candidate commercially the same offering or a distinct offering?** 
   - If distinct, propose a **New Product Family**. If the same, propose **Attachment** (requiring resolution of `internal_id`).
7. **If uncertainty remains $\rightarrow$ Human Approval Required.** 
   - Business judgment is required for edge cases.

---

## 2. Confidence & Signal-Combination Semantics

A high model score does not itself create canonical truth. Confidence semantics define the cognitive output decision classes.

> **OPEN BUSINESS DECISION:** Numeric thresholds defining these classes are unresolved and require business determination.

### 2.1 Signal Types
- **Deterministic Signals:** Explicit UUIDs, exact canonical discoveries. These have absolute veto power.
- **Probabilistic Signals:** Image embeddings, NLP text similarity. 

### 2.2 Semantic Decision Classes
- **Deterministic Match:** Unquestionable identifier resolution mapping to a `DISCOVERED_CANONICAL` internal ID.
- **Strong Candidate:** High-confidence semantic/visual alignment across probabilistic signals.
- **Ambiguous Candidate:** Borderline match, or conflicting strong signals (e.g., text matches Family A, image matches Family B).
- **No Viable Candidate:** Clearly distinct from all existing entities in `vw_catalog_master`.
- **Human Approval Required:** Safety fallback for ambiguity, missing evidence, or conflicting deterministic signals.

---

## 3. SKU Generation & Bounded Collision Retries

Catalog ID derives candidate `sku_id` strings based on heuristics (e.g., `126BS-BLU`). 

If Catalog BS rejects the proposal with a `SKU_COLLISION` (or if public views flag it during discovery), Catalog ID executes a bounded, deterministic retry strategy.

### 3.1 Bounded Retry Semantics
- **Rule:** Catalog ID must NOT endlessly or blindly mutate identifiers until Catalog BS accepts one. Random uncontrolled generation is prohibited.
- **Mutation Sequence:** The information changed between attempts must follow a deterministic heuristic (e.g., Base $\rightarrow$ Append Size $\rightarrow$ Append Variant Numeral).

> **OPEN DECISION / CONFIGURATION REQUIRED:** The exact maximum number of automated proposal attempts is an open business decision (e.g., maximum 3 attempts). 

### 3.2 Post-Failure Termination
The retry mechanism must always terminate in one of three states:
1. **Successful Command:** Catalog BS accepts the proposal.
2. **Deterministic Failure:** All retries exhaust, halting the session.
3. **Human Escalation:** The session pauses, presenting the original collision reason from Catalog BS to the operator for manual resolution.
