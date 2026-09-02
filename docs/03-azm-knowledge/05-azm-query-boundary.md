# Azm Query Boundary

**Document Reference:** `docs/03-azm-knowledge/05-azm-query-boundary.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Authoritative Access Boundary

The flow of semantic and schematic knowledge to Aaram's AI capabilities is strictly governed by the following invariant:

**INTENDED:** `BRAIN → AZM → KNOWLEDGE`
**FORBIDDEN:** `BRAIN → BUSINESS SYSTEM PUBLIC CONTRACT`
**FORBIDDEN:** `BRAIN → BUSINESS SYSTEM DATABASE` (for meaning)

Brain Core is entirely blind to the meaning of the ecosystem without Azm. It cannot bypass Azm to read a markdown file or reverse-engineer a DDL script.

---

## 2. What Brain is Allowed to Ask Azm

Brain Core interacts with Azm via a logical query boundary. Brain is permitted to request:

### 2.1 Concept Resolution
- *"What is a SKU?"* (Returns the Semantic Definition).
- *"What are the synonyms for a Packing Slip?"* (Returns the Vocabulary).

### 2.2 Relational Navigation
- *"What concepts belong to the Catalog domain?"*
- *"What concepts are children of a Product?"*

### 2.3 Schematic Retrieval
- *"How do I query the active SKU data?"* (Returns the Schematic Reference, e.g., `vw_catalog_skus`).
- *"Which field in this schema maps to the 'Selling Price' concept?"* (Returns the Attribute Mapping).

### 2.4 Provenance & Context
- *"Which Business System owns this concept?"*
- *"Is this concept Aaram-native or an external channel concept?"*
- *"Is this schematic mapping active or deprecated?"*

---

## 3. The Execution Handoff

Azm provides **Knowledge**. Brain Core executes **Action**.

1. Brain asks Azm: *"Where is Inventory data?"*
2. Azm replies: *"It is governed by the Inventory BS, exposed via `vw_stock_balances`."*
3. Brain uses its own execution engine (not Azm) to execute a SQL query against `vw_stock_balances` in the operational database.

Azm is out of the loop the moment actual operational data is queried.
