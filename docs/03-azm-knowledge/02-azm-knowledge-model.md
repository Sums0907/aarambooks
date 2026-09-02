# Azm Logical Knowledge Model

**Document Reference:** `docs/03-azm-knowledge/02-azm-knowledge-model.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Purpose
Azm requires a strictly defined **Logical Knowledge Model** independent of physical database implementation. This document defines the minimum logical primitives Azm needs to represent semantic and schematic knowledge derived from Business System contracts.

---

## 2. Logical Primitives

### 2.1 Namespace / Domain
- **What it represents:** The high-level boundary of knowledge ownership (e.g., `inventory`, `catalog`).
- **Why Azm needs it:** To logically partition knowledge and trace it back to the authoritative Business System.

### 2.2 Semantic Concept
- **What it represents:** An atomic business idea declared by a Business System (e.g., `SKU`, `Product`).
- **Why Azm needs it:** It is the core building block of all ecosystem intelligence.
- **Attributes:** Azm Knowledge Identity (UUID), Name, Definition, Aliases/Vocabulary.

### 2.3 Semantic Relationship
- **What it represents:** A directional meaning connecting concepts, crucially bridging multiple Business Systems (e.g., Catalog `SKU` *has* Inventory `Stock Balance`).
- **Why Azm needs it:** To allow Brain Core to navigate the unified ecosystem ontology.

### 2.4 Schematic Reference (View / Schema)
- **What it represents:** The governed machine-readable surface area exposed by a Business System (e.g., `vw_catalog_skus`).
- **Why Azm needs it:** Brain Core needs to know exactly which SQL views or APIs to call to execute operational data retrieval.

### 2.5 Attribute Mapping
- **What it represents:** The link between a Semantic Concept and a specific field in a Schematic Reference.
- **Why Azm needs it:** To translate abstract AI reasoning into precise data queries.

### 2.6 External / Channel Mapping
- **What it represents:** The relationship between an Aaram-native concept and a foreign channel concept (e.g., Aaram `SKU` maps to ShopDeck `customer_sku_short_id`).
- **Why Azm needs it:** To safely interact with external systems without corrupting Aaram's native semantic authority.

### 2.7 Knowledge Provenance & Lineage
- **What it represents:** The metadata tracking the origin of a knowledge primitive (Source BS -> Contract -> Version -> Ingestion Run).
- **Why Azm needs it:** To prove that a Concept exists because it was explicitly declared by a governed authority, and to distinguish Source Identity from Azm Knowledge Identity.

---

## 3. Explicit Distinctions

The logical model strictly enforces the difference between:

1. **CANONICAL OPERATIONAL TRUTH:** The actual operational records. (Owned by BS. *Not stored in Azm*).
2. **PUBLIC CONTRACT DECLARATION:** The markdown/DDL file declaring semantics and schemas. (Owned by BS. *Source material, not stored in Azm*).
3. **AZM KNOWLEDGE:** The persistent `Semantic Concept` node in Azm's logical model, derived from the contract. (Owned by Azm. *Stored in Azm*).
