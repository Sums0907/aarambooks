# Azm Logical Knowledge Model

**Document Reference:** `docs/03-azm-knowledge/02-azm-knowledge-model.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Purpose
Before selecting a physical database technology (PostgreSQL, Graph, Vector, etc.), Azm requires a strictly defined **Logical Knowledge Model**. This document defines the minimum logical primitives Azm needs to represent semantic and schematic knowledge derived from Business System contracts.

---

## 2. Logical Primitives

### 2.1 Namespace / Domain
- **What it represents:** The high-level boundary of knowledge ownership (e.g., `inventory`, `ndr`, `catalog`).
- **Why Azm needs it:** To logically partition knowledge and trace it back to the authoritative Business System that owns the domain.

### 2.2 Semantic Concept
- **What it represents:** An atomic business idea defined by a Business System (e.g., `SKU`, `Product`, `Posting Date`).
- **Why Azm needs it:** It is the core building block of all ecosystem intelligence. Brain Core needs to understand what these concepts mean to reason accurately.
- **Attributes:** Name, Definition, Aliases/Synonyms.

### 2.3 Semantic Relationship
- **What it represents:** A directional meaning between two concepts (e.g., `Product` *contains* `SKU`).
- **Why Azm needs it:** To allow Brain Core to navigate the business ontology and understand dependencies.

### 2.4 Schematic Reference (View / Schema)
- **What it represents:** The governed machine-readable surface area exposed by a Business System (e.g., `vw_catalog_skus`).
- **Why Azm needs it:** Brain Core needs to know exactly which SQL views or APIs to call to retrieve operational data for a semantic concept.

### 2.5 Attribute Mapping
- **What it represents:** The link between a Semantic Concept and a specific field in a Schematic Reference (e.g., The concept `SKU Identity` maps to `sku_id` in `vw_catalog_skus`).
- **Why Azm needs it:** To translate abstract AI reasoning into precise data queries.

### 2.6 External / Channel Mapping
- **What it represents:** The relationship between an Aaram-native concept and a foreign channel concept (e.g., Aaram `SKU` maps to ShopDeck `customer_sku_short_id`).
- **Why Azm needs it:** To safely interact with external systems without corrupting Aaram's native semantics.

### 2.7 Knowledge Provenance
- **What it represents:** The metadata tracking the origin of a knowledge primitive.
- **Why Azm needs it:** Azm must never invent truth. It must prove that a Concept exists because it was explicitly declared in version `v1.2` of the `Catalog Semantic Public Contract`.

---

## 3. Explicit Distinctions

The logical model strictly enforces the difference between:

1. **CANONICAL OPERATIONAL TRUTH:** The actual row in the `catalog_skus` table in the database. (Owned by BS. Not stored in Azm).
2. **PUBLIC CONTRACT DECLARATION:** The markdown document or SQL DDL declaring that the `SKU` concept exists and is exposed. (Owned by BS. Not stored in Azm).
3. **AZM KNOWLEDGE:** The persistent `Semantic Concept` node in Azm's logical model, derived from the contract. (Owned by Azm. Stored in Azm).
