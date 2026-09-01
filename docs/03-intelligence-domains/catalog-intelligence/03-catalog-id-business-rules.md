# Catalog ID Business Rules & Heuristics

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/03-catalog-id-business-rules.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.0
**Last Updated:** September 1, 2026

---

## 1. Product Family Reasoning Framework

Catalog ID determines if an intake candidate belongs to an existing family or constitutes a new product. It applies the following hierarchical reasoning framework:

1. **Is canonical identity explicitly supplied?** 
   - If the user provides a direct `product_internal_id` or existing `product_code`, evaluate for direct attachment.
2. **Is there a deterministic existing-entity match?** 
   - E.g., Barcode lookup or explicit SKU ID match.
3. **Does the candidate represent the same underlying commercial design?** 
   - Are the lifestyle images, fabric, and base structure identical?
4. **Are differences only variant-level attributes?** 
   - Are the only variations in color, size, or packaging?
5. **Does product construction/component composition remain materially the same?** 
   - A single bedsheet vs a bedsheet + pillow cover set are typically different products.
6. **Is the candidate commercially the same offering or a distinct offering?** 
   - If distinct, propose a **New Product Family**. If the same, propose **Attachment**.
7. **If uncertainty remains $\rightarrow$ Human Approval Required.** 
   - Do not force edge cases into automated rules.

---

## 2. Confidence & Signal-Combination Semantics

Numeric thresholds are treated as **OPEN / DECISION REQUIRED** business configurations. However, the reasoning model evaluates signals to assign a semantic decision class.

### 2.1 Signal Types
- **Deterministic Signals:** Explicit UUIDs, barcodes, exact `product_code` matches provided by the user. These have absolute veto power.
- **Probabilistic Signals:** Image embeddings, NLP similarity of descriptions. 

### 2.2 Signal Combination Rules
- **Veto Power:** A deterministic mismatch (e.g., user supplies `product_code A`, but image clearly matches `product_code B`) immediately forces **Human Approval Required**.
- **Conflicting Strong Signals:** If semantic text similarity is high but visual similarity is low, the assessment is **Ambiguous Candidate**.
- **Missing Evidence:** Lack of an image or a partial description lowers confidence, typically preventing a "Strong Candidate" classification.

### 2.3 Semantic Decision Classes
- **Deterministic Match:** Unquestionable identifier resolution.
- **Strong Candidate:** High-confidence alignment across all available signals.
- **Ambiguous Candidate:** Borderline match or conflicting signals.
- **No Viable Candidate:** Clearly distinct from all existing entities.
- **Human Approval Required:** Safety fallback for conflicts, rejections, or missing data.

---

## 3. SKU Generation & Bounded Collision Retries

Catalog ID derives candidate `sku_id` strings (e.g., translating "Royal Blue Bedsheet" into `126BS-BLU`) based on extraction heuristics. 

If Catalog BS rejects the proposal with a `SKU_COLLISION` (or if public views show it as active), Catalog ID executes bounded deterministic retries:

### 3.1 Bounded Retry Semantics
1. **Attempt 1 (Base Heuristic):** `[CategoryAcronym]-[ColorAcronym]` (e.g., `BS-BLU`).
2. **Attempt 2 (Size Disambiguation):** Append size marker (e.g., `BS-BLU-KG`).
3. **Attempt 3 (Numeric Disambiguation):** Append variant numeral (e.g., `BS-BLU-02`).
4. **Max Attempts Reached:** Catalog ID is strictly limited to a **maximum of 3 automated proposal attempts**. 

> **OPEN GAP / DECISION REQUIRED:** The exact maximum number of retries is configurable, but 3 is recommended to prevent blind mutation loops.

### 3.2 Post-Failure Escalation
If Attempt 3 is rejected by Catalog BS, Catalog ID **must** halt automation and escalate to **Human Approval Required**. The original collision reason from Catalog BS must be preserved in the `IntakeSession` log for the operator to review.
