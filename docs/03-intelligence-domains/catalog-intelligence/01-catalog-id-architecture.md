# Catalog ID (Catalog Intelligence) Overview & Architecture

**Document Reference:** `docs/03-intelligence-domains/catalog-intelligence/01-catalog-id-architecture.md`
**System Name:** Catalog Intelligence Domain (`Catalog ID`)
**Domain Layer:** Cognitive Intelligence Layer
**Status:** Canonical Intelligence Specification
**Authoritative Version:** 2.1
**Last Updated:** September 1, 2026

---

## 1. Purpose & Business Problem

Catalog creation is historically manual, tedious, and error-prone. Operators must format spreadsheets, deduce appropriate SKU codes, construct descriptions, and ensure strict compliance with business rules. 

Catalog ID provides an intelligent intake funnel that interprets human intent, extracts relevant attributes, reasons about product families, and formulates a structured catalog command. It acts strictly as a **cognitive client** to the Catalog Business System (`Catalog BS`).

---

## 2. Architectural Boundaries & Core Invariant

Catalog ID operates under a strict, non-negotiable invariant:

$$\mathbf{Catalog\ ID\ THINKS\ \&\ PROPOSES} \longrightarrow \mathbf{Catalog\ BS\ VALIDATES\ \&\ PERSISTS} \longrightarrow \mathbf{Database\ STORES\ TRUTH}$$

### 2.1 What Catalog ID Owns (In Scope)
- **Cognitive Intake:** Parsing natural language, analyzing images, understanding unstructured input.
- **Attribute Extraction & Classification:** Identifying colors, dimensions, fabrics, classifying provenance (`USER_SUPPLIED`, `EXTRACTED`, `INFERRED`).
- **Product Family Reasoning:** Evaluating whether a requested item belongs to an existing product family or constitutes a new one.
- **SKU Generation Heuristics:** Proposing candidate `sku_id` strings and executing bounded, deterministic retries upon rejection.
- **Structured Command Generation:** Formatting the final intent into a compliant Catalog BS mutation (`SaveProductFamily`).

### 2.2 What Catalog ID Does NOT Own (Out of Scope)
- **NO Canonical Truth:** Catalog ID must **never** own canonical Product/SKU truth, become a Product/SKU master, or maintain a shadow Product/SKU database.
- **NO Database Validation:** Catalog ID does not independently enforce uniqueness as an authority. It proposes; Catalog BS validates.
- **NO Direct Database Access:** Catalog ID must never directly access or mutate Catalog BS database tables. It uses authorized read views and mutation contracts.
- **NO Internal ID Sovereignty:** Catalog ID must never independently generate authoritative `internal_id` (UUID) values for canonical persistence.

---

## 3. Historical Identity & Public Read Contract

Catalog BS enforces strict historical non-reuse of identifiers (`sku_id`, `product_code`) via its reservation ledgers (`catalog_sku_id_reservations`, `catalog_product_code_reservations`). Catalog ID cannot query these physical ledgers directly.

Therefore, the architectural strategy is:
**Best-Effort Proactive Discovery + Authoritative Enforcement via Catalog BS.**

- **Discovery:** Catalog ID queries the Catalog BS public read contracts (`vw_catalog_master`, `vw_catalog_products`, `vw_catalog_skus`) to discover known identifiers and proactively avoid obvious collisions.
- **Enforcement:** The public views provide a snapshot, but Catalog BS remains the **ONLY** authoritative collision authority. Catalog ID must not claim that a public-view lookup guarantees collision-free creation. A race can still occur after discovery. If Catalog BS rejects a proposed identifier (`SKU_COLLISION`, `PRODUCT_CODE_COLLISION`), Catalog ID must treat that rejection as authoritative and final.

---

## 4. Technology Agnosticism

This specification defines the **logical architecture** of Catalog ID. It explicitly defines *what* Catalog ID must do, not *how*. 

Technology-specific implementations (e.g., specific ML models, embeddings, vector search, LLM vendors, databases, Qwen, RABTA) are strictly deferred to the physical implementation phase unless an authoritative project document explicitly requires them.
