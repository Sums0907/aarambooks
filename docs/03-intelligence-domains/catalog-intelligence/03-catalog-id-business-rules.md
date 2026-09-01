# Catalog ID Business Rules & Heuristics

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/03-catalog-id-business-rules.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 1.0
**Last Updated:** September 1, 2026

---

## 1. Product Family Reasoning Framework

As established by Catalog BS (`ADR-RUL-001`), the cognitive reasoning to determine product-family grouping resides in Catalog ID.

### 1.1 The Decision Framework
Catalog ID evaluates new intake candidates against the existing catalog (discovered via `vw_catalog_master`). It must answer: *Is this a selectable variation of an existing commercial offering, or a fundamentally new concept?*

- **Attachment (Sibling SKU):** If the candidate is merely a new color, size, or pack configuration of an existing design, Catalog ID resolves the authoritative existing Product `internal_id` and proposes an attachment command.
- **New Family:** If the candidate represents a distinct flagship design, different component structure, or new category, Catalog ID proposes a new Product family with a new `product_code`.

### 1.2 The `product_code` Membership Rule
**CRITICAL INVARIANT:** A matching `product_code` string **MUST NOT** automatically cause a new SKU to be attached to an existing Product.
- Catalog ID may use `product_code` as a *discovery/search signal*.
- To propose an attachment, Catalog ID **must** resolve the exact Product `internal_id` and explicitly target it in the `SaveProductFamily` command.

---

## 2. Confidence Semantics & Decision Classes

Catalog ID does not rely on a universal ">= 90% = automation" rule. Resolution decisions are categorized into explicit semantic classes.

> **OPEN GAP / DECISION REQUIRED:** Specific numeric thresholds mapping to these semantic classes remain undefined and must be calibrated based on business risk tolerance.

| Decision Class | Definition | Action Taken by Catalog ID |
|---|---|---|
| **Deterministic Match** | Exact identifier match (e.g., Barcode or explicit UUID provided). | Automates generation of update/attachment command targeting `internal_id`. |
| **Strong Candidate** | High-confidence semantic/visual alignment (numeric threshold pending). | Automates generation of proposal. |
| **Ambiguous Candidate** | Borderline match; risks false positive collision. | Halts automation. Routes `ResolutionDecision` to human-in-the-loop. |
| **No Viable Candidate** | Clearly distinct from all existing catalog entities. | Automates generation of a New Product family proposal. |
| **Human Approval Required**| Safety fallback for unparseable input or explicit manual review flags. | Halts automation. Escalates to human. |

---

## 3. SKU Generation Heuristics

Catalog ID is responsible for proposing candidate `sku_id` strings (e.g., translating "Royal Blue Bedsheet" into `126BS-BLU`).

### 3.1 Logical Heuristic Process
1. **Derivation:** Catalog ID extracts key differentiating attributes (color, size, category) and applies a formatting heuristic to generate a base string (e.g., `[CategoryNum][CatAcronym]-[ColorAcronym]`).
2. **Pre-flight Discovery:** Catalog ID queries public read views (`vw_catalog_master`) to check if the proposed string is already in use.
3. **Collision Avoidance:** If the string is found in the public views, Catalog ID applies a disambiguation strategy (e.g., appending a size marker or variant numeral) to generate a novel candidate.
4. **Proposal:** The candidate `sku_id` is included in the command payload.

### 3.2 Authority Boundary
- Catalog ID **proposes** the `sku_id` and attempts to avoid obvious collisions based on current public data.
- Catalog BS **enforces** final uniqueness, syntax ($5 \le \text{len} \le 10$, uppercase), and permanent historical non-reuse.
- If Catalog BS rejects the proposal with a `SKU_COLLISION` error, Catalog ID must catch the rejection, execute its disambiguation heuristic again, and retry or escalate.
