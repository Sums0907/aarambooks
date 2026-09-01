# Catalog ID (Catalog Intelligence) Overview & Architecture

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/01-catalog-id-architecture.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer (Box 1 in Aaram Ecosystem)
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 1.0
**Last Updated:** September 1, 2026

---

## 1. Purpose & Business Problem

### 1.1 The Operational Problem
Catalog creation is historically manual, tedious, and error-prone. Operators must format 46-column spreadsheets, deduce appropriate SKU codes, construct SEO-optimized descriptions, and ensure strict compliance with business rules. This creates friction, slows down new product launches, and increases the likelihood of data entry errors.

### 1.2 Primary Business Objective
Catalog ID exists to solve this problem by providing a cognitive intelligence layer. It acts as an "intelligent intake funnel" that interprets human intent (via natural language or images), extracts relevant attributes, reasons about product families, and formulates a structured catalog command.

---

## 2. Architectural Boundaries & Core Invariant

Catalog ID operates under a strict, non-negotiable invariant:

$$\mathbf{Catalog\ ID\ THINKS\ \&\ PROPOSES} \longrightarrow \mathbf{Catalog\ BS\ VALIDATES\ \&\ PERSISTS} \longrightarrow \mathbf{Database\ STORES\ TRUTH}$$

### 2.1 What Catalog ID Owns (In Scope)
- **Cognitive Intake:** Parsing natural language, analyzing images, and understanding unstructured input.
- **Attribute Extraction:** Identifying colors, dimensions, fabrics, and configurations.
- **Product Family Reasoning:** Evaluating whether a requested item belongs to an existing product family or constitutes a new one.
- **SKU Generation Heuristics:** Proposing clean, human-readable candidate `sku_id` strings (e.g., extracting color acronyms).
- **SEO & Content Generation:** Proposing titles, descriptions, and taxonomy categorizations.
- **Structured Command Generation:** Formatting the final intent into a `SaveProductFamily` command payload.

### 2.2 What Catalog ID Does NOT Own (Out of Scope)
- **NO Canonical Truth:** Catalog ID must **never** become a second Product/SKU master. It does not own canonical catalog data.
- **NO Database Validation:** Catalog ID does not enforce uniqueness or data integrity. It proposes; Catalog BS validates.
- **NO Direct Database Access:** Catalog ID never reads from or writes to the internal physical tables of Catalog BS.

---

## 3. The Intake & Resolution Pipeline

The lifecycle of a Catalog ID interaction follows this pipeline:

1. **Intake:** Unstructured input is received (e.g., "Add this blue floral bedsheet", plus an image).
2. **Discovery (Read):** Catalog ID queries the Catalog BS public read contracts (`vw_catalog_master`) to understand the current catalog landscape.
3. **Reasoning & Extraction:** Catalog ID extracts attributes and reasons about product family membership.
4. **Resolution Decision:**
   - If a high-confidence match is found, it proposes attaching the new SKU to the existing Product via `internal_id`.
   - If no viable match exists, it proposes creating a new Product family.
   - If ambiguous, it halts and requests human clarification.
5. **Command Generation (Write):** Catalog ID submits a structured `SaveProductFamily` mutation to Catalog BS.

---

## 4. Technology Agnosticism

This specification defines the **logical architecture** of Catalog ID. It explicitly does not mandate specific implementation technologies (e.g., specific ML models, vector databases, or embedding strategies) unless required by downstream authoritative documents. The focus is strictly on cognitive boundaries and resolution semantics.
