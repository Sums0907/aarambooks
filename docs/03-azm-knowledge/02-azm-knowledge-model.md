# Azm Logical Knowledge Model

**Document Reference:** `docs/03-azm-knowledge/02-azm-knowledge-model.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Purpose
Azm requires a strictly defined **Logical Knowledge Model** independent of physical database implementation. This document defines the minimum logical primitives Azm needs to represent semantic and schematic knowledge derived from Business System contracts.

The model distinguishes between **source-declared knowledge** (explicitly declared in a BS Public Contract and faithfully ingested by AZM) and **AZM-derived ecosystem knowledge** (inferred by AZM from relationships across multiple BS contracts). Both categories are first-class knowledge nodes in AZM, but their provenance differs.

---

## 2. Logical Primitives

### 2.1 Namespace / Domain
- **What it represents:** The high-level boundary of knowledge ownership (e.g., `inventory`, `catalog`).
- **Why Azm needs it:** To logically partition knowledge and trace it back to the authoritative Business System.
- **Classification:** Must carry a namespace classification: `AARAM_NATIVE` (derived from an Aaram Business System) or `EXTERNAL_CHANNEL` (derived from an external system such as ShopDeck). These classifications are structurally distinct — `EXTERNAL_CHANNEL` knowledge cannot redefine `AARAM_NATIVE` concepts.

### 2.2 Semantic Concept
- **What it represents:** An atomic business idea declared by a Business System (e.g., `SKU`, `Product`).
- **Knowledge kind:** Source-declared (explicitly stated in BS Semantic Public Contract).
- **Why Azm needs it:** It is the core building block of all ecosystem intelligence.
- **Attributes:** Azm Knowledge Identity (UUID), Name, Definition, Aliases/Vocabulary, Namespace, Provenance Reference, Knowledge Version, Lifecycle State (ACTIVE / DEPRECATED / ARCHIVED).

### 2.3 Semantic Relationship
- **What it represents:** A directional meaning connecting concepts, crucially bridging multiple Business Systems (e.g., Catalog `SKU` *has* Inventory `Stock Balance`).
- **Knowledge kind:** May be source-declared (if a BS contract explicitly declares a relationship to another domain concept) OR AZM-derived (if AZM infers the relationship from two independent BS contracts). The knowledge kind must be recorded in provenance.
- **Why Azm needs it:** To allow Brain Core to navigate the unified ecosystem ontology.

### 2.4 Schematic Reference (View / Schema)
- **What it represents:** The governed machine-readable surface area exposed by a Business System (e.g., `vw_catalog_skus`). This is the view/API/MCP surface itself — its name, description, owning BS, and version.
- **Knowledge kind:** Source-declared (explicitly stated in BS Schematic Public Contract).
- **Why Azm needs it:** Brain Core needs to know exactly which SQL views or APIs to call to execute operational data retrieval.

### 2.5 Schematic Attribute
- **What it represents:** An individual exposed field within a Schematic Reference (e.g., `sku_id VARCHAR` in `vw_catalog_skus`), including its data type, description, and the Semantic Concept it corresponds to.
- **Knowledge kind:** Source-declared (from the BS Schematic Public Contract field definitions).
- **Why Azm needs it:** Brain Core must know which field to query when reasoning about a specific concept. Without field-level knowledge, AZM cannot answer "Which field in `vw_catalog_skus` represents the selling price?" AZM cannot answer conceptual questions through view-level knowledge alone.

### 2.6 Attribute Mapping
- **What it represents:** The explicit link between a Semantic Concept and a specific Schematic Attribute (e.g., Concept `catalog.sku.selling_price` ↔ Field `selling_price` in `vw_catalog_skus`).
- **Knowledge kind:** Source-declared or AZM-derived (if the mapping is inferable but not explicitly named in the contract).
- **Why Azm needs it:** To translate abstract AI reasoning ("find the selling price of a SKU") into precise data access ("query `selling_price` from `vw_catalog_skus` WHERE `sku_id = ?`").

### 2.7 External / Channel Mapping
- **What it represents:** The relationship between an Aaram-native concept and a foreign channel concept (e.g., Aaram `SKU` maps to ShopDeck `customer_sku_short_id`).
- **Knowledge kind:** Source-declared (from the BS Semantic Contract's channel reconciliation section) or AZM-tagged (when AZM classifies an ingested concept as external).
- **Why Azm needs it:** To safely interact with external systems without corrupting Aaram's native semantic authority. These mappings are always subordinate to the canonical `AARAM_NATIVE` concept they reference.

### 2.8 Knowledge Provenance & Lineage
- **What it represents:** The metadata tracking the origin of a knowledge primitive.
- **Why Azm needs it:** To prove that a Concept exists because it was explicitly declared by a governed authority, and to distinguish Source Identity from Azm Knowledge Identity. Derived knowledge must explicitly record its derivation method and source contracts.

**Provenance for Source-Declared Knowledge:**
```
Business System → Contract Type (Semantic|Schematic) → Contract Version/Hash
  → Specific Declaration Element → Ingestion Run → Azm Knowledge Identity
```

**Provenance for AZM-Derived Knowledge:**
```
[Source BS A Contract + Source BS B Contract] → Derivation Method
  → Derivation Basis (what elements were combined) → Ingestion Run
  → Azm Knowledge Identity
```

---

## 3. Explicit Distinctions

The logical model strictly enforces the difference between:

1. **CANONICAL OPERATIONAL TRUTH:** The actual operational records. (Owned by BS. *Not stored in Azm*).
2. **PUBLIC CONTRACT DECLARATION:** The markdown/DDL file declaring semantics and schemas. (Owned by BS. *Source material — not stored as AZM's knowledge object. AZM creates its own derived knowledge nodes*).
3. **AZM SOURCE-DECLARED KNOWLEDGE:** The persistent `Semantic Concept` or `Schematic Reference` node in Azm's logical model, faithfully derived from an explicit contract declaration. (Owned by Azm. *Stored in Azm with full source provenance*).
4. **AZM DERIVED KNOWLEDGE:** The persistent `Semantic Relationship` or `Attribute Mapping` node that AZM constructs by reasoning across multiple contract declarations. (Owned by Azm. *Stored in Azm with derivation provenance — records which contracts were combined and by what method*).

---

## 4. Schematic Knowledge is More Than a View List

Azm's schematic knowledge is explicitly required to answer all of the following questions:

| Question | AZM Primitive Required |
|---|---|
| Which BS owns this concept? | Namespace → Provenance |
| Which public surface exposes it? | Schematic Reference |
| Which view/API/MCP surface represents it? | Schematic Reference |
| Which attributes are exposed? | Schematic Attribute |
| What does each exposed field represent? | Attribute Mapping |
| Which concept does an exposed field correspond to? | Attribute Mapping |
| What is the relationship between semantic concepts and schematic elements? | Attribute Mapping + Semantic Relationship |
| Which version of the schematic declaration produced this knowledge? | Provenance on Schematic Reference |
| Is the exposure current, deprecated, or historical? | Lifecycle State on Schematic Reference / Attribute |

A Schematic Reference that stores only the view name and a description is **insufficient**. Azm must persist individual Schematic Attributes (columns/fields) as first-class knowledge nodes.
