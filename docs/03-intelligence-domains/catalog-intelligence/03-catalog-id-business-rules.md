# Catalog ID Business Rules & Heuristics

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/03-catalog-id-business-rules.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.2
**Last Updated:** September 1, 2026

---

## 1. Product Family Reasoning Framework

Catalog ID determines if an intake candidate represents an existing family or constitutes a new product. This reasoning evaluates similarity to generate a *proposal*; it does not create canonical identity.

**Reasoning Hierarchy:**
1. **Is canonical identity explicitly supplied?** (Direct `product_internal_id`)
2. **Is there a deterministic existing-entity match?** (Exact barcode map to `DISCOVERED_CANONICAL` `internal_id`)
3. **Does the candidate represent the same underlying commercial design?** 
4. **Are differences only variant-level attributes?** 
5. **Does product construction/component composition remain materially the same?** 
6. **Is the candidate commercially the same offering or a distinct offering?** 
7. **If uncertainty remains $\rightarrow$ Human Approval Required.** 

---

## 2. Confidence Precedence & Signal Resolution

A high probabilistic score must **never** override a deterministic contradiction. The precedence model for evaluating and combining evidence is explicitly defined as:

1. **Explicit authoritative canonical identity:** (e.g., User supplies a known `product_internal_id`). This holds absolute authority for family attachment.
2. **Deterministic canonical match:** (e.g., Verified barcode match).
3. **Hard contradiction detection:** (e.g., Deterministic match found, but user provides a conflicting canonical identity).
4. **Probabilistic evidence aggregation:** (e.g., AI vision matches images, NLP matches description).
5. **Semantic decision class:** Final cognitive classification.

### 2.1 Handling Uncertainty and Conflict

These states are distinct and must not be handled identically:

- **LOW CONFIDENCE:** The aggregated probabilistic evidence falls below acceptable thresholds.
  $\rightarrow$ **Action:** Route to `Ambiguous Candidate` / `Human Approval Required`.
- **CONFLICTING STRONG SIGNALS:** Different evidence vectors strongly suggest mutually exclusive facts (e.g., text explicitly describes "Family A" but the visual embedding strongly matches "Family B").
  $\rightarrow$ **Action:** Route to `Human Approval Required`.
- **DETERMINISTIC CONTRADICTION:** An absolute, logical violation of facts (e.g., user explicitly provides `product_internal_id` of a bedsheet, but provides a deterministic barcode for a pressure cooker). 
  $\rightarrow$ **Action:** **NEVER** auto-attach. This requires explicit human resolution or immediate rejection.

*(Numeric confidence thresholds mapping to these states remain an OPEN BUSINESS DECISION and are not defined here).*

---

## 3. SKU Generation & Bounded Collision Retries

Catalog ID derives candidate `sku_id` strings based on heuristics. If Catalog BS rejects the proposal with a `SKU_COLLISION`, Catalog ID executes a bounded, deterministic retry strategy.

### 3.1 Retry Semantics & Restrictions
- **Example Heuristic Sequence:** Base $\rightarrow$ Append Size $\rightarrow$ Append Variant Numeral. *(Note: This is an example heuristic only, not a frozen SKU-generation algorithm).*
- **Configuration Requirement:** The retry count remains an open policy/configuration decision. Do not invent a mandatory numeric limit here.
- **Deterministic and Bounded:** Every retry must be deterministic and bounded to the configured limit.
- **Identity Protection:** Retries must not mutate canonical identity; they only mutate the proposed candidate string.
- **Termination:** Retries must always terminate in success, deterministic failure, or human escalation.
- **Final Authority:** Catalog BS remains the final authority on whether a retry succeeds.
