# Catalog ID (Catalog Intelligence) Overview & Architecture

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/01-catalog-id-architecture.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.0
**Last Updated:** September 1, 2026

---

## 1. Purpose & Business Problem

Catalog creation is historically manual, tedious, and error-prone. Operators must format 46-column spreadsheets, deduce appropriate SKU codes, construct SEO-optimized descriptions, and ensure strict compliance with business rules. Catalog ID exists to provide an intelligent intake funnel that interprets human intent, extracts relevant attributes, reasons about product families, and formulates a structured catalog command.

---

## 2. Architectural Boundaries & Core Invariant

Catalog ID operates under a strict, non-negotiable invariant:

$$\mathbf{Catalog\ ID\ THINKS\ \&\ PROPOSES} \longrightarrow \mathbf{Catalog\ BS\ VALIDATES\ \&\ PERSISTS} \longrightarrow \mathbf{Database\ STORES\ TRUTH}$$

### 2.1 What Catalog ID Owns (In Scope)
- **Cognitive Intake:** Parsing natural language, analyzing images, understanding unstructured input.
- **Attribute Extraction & Classification:** Identifying colors, dimensions, fabrics, classifying provenance (`USER_SUPPLIED`, `EXTRACTED`, `INFERRED`).
- **Product Family Reasoning:** Evaluating whether a requested item belongs to an existing product family or constitutes a new one.
- **SKU Generation Heuristics:** Proposing candidate `sku_id` strings and executing bounded retries upon collision.
- **Structured Command Generation:** Formatting the final intent into a compliant Catalog BS mutation.

### 2.2 What Catalog ID Does NOT Own (Out of Scope)
- **NO Canonical Truth:** Catalog ID must **never** become a second Product/SKU master.
- **NO Database Validation:** Catalog ID does not enforce uniqueness. It proposes; Catalog BS validates.
- **NO Direct Database Access:** Catalog ID never reads from or writes to the physical tables or reservation ledgers of Catalog BS.

---

## 3. Historical Identity & Public Read Strategy

Catalog BS enforces strict historical non-reuse of identifiers (`sku_id`, `product_code`) via its reservation ledgers. Catalog ID cannot query these physical ledgers directly.

Therefore, the architectural strategy is:
**Best-Effort Proactive Discovery + Authoritative Enforcement via Catalog BS.**

- **Discovery:** Catalog ID queries the Catalog BS public read contracts (`vw_catalog_master`, `vw_catalog_products`, `vw_catalog_skus`) to discover known identifiers and proactively avoid obvious collisions.
- **Enforcement:** The public views are not guaranteed to expose every historical tombstone. Catalog BS remains the **ONLY** authoritative collision authority. Catalog ID expects and handles rejections (`SKU_COLLISION`, `PRODUCT_CODE_COLLISION`) as standard, deterministic enforcement mechanisms, not system failures.

---

## 4. Technology Agnosticism

This specification defines the **logical architecture** of Catalog ID. It explicitly does not mandate specific implementation technologies (e.g., specific ML models, vector databases, or embedding strategies) unless required by downstream authoritative documents. The focus is strictly on cognitive boundaries and resolution semantics.
