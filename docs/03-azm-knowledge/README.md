# Azm (Aaram Zameer): The Semantic & Schematic Repository

**Document Reference:** `docs/03-azm-knowledge/README.md`
**System Name:** Aaram Zameer (`Azm`)
**Domain Layer:** Central Knowledge Registry (Container 3)
**Classification:** Foundational Architecture & Boundary Grounding

---

## 1. The Soul of Azm

**Azm (عزم)** is an Urdu word meaning **resolve** and **determination**. It was designed with a very personal and deep connection to the Aaram ecosystem.

Azm is the **global persistent repository of the semantic and schematic knowledge** of the entire ecosystem. It does not just hold data — it normalizes, versions, and represents the governed knowledge declared by Business Systems across domain boundaries.

**Precise Definition:**
> AZM is AaramBooks' persistent semantic-and-schematic knowledge layer. It owns the **persistent knowledge representation** derived from governed Business System Public Contracts. Business Systems declare authoritative domain meaning; AZM normalizes, versions, and persists that declared knowledge — including how concepts relate across systems and how governed public schemas expose them. AZM is NOT the semantic authority. AZM's knowledge is stored in its own independent persistent database — it is NOT a repository of the source contracts themselves.

It explicitly **DOES NOT** own:
- canonical operational business truth
- operational business records
- transactional state
- business workflow execution
- runtime context extraction
- business-rule enforcement
- the source Semantic or Schematic Public Contracts themselves (those remain owned by the Business System)

---

## 2. The Cognitive Split: The 4-Box Separation of Concerns

The ecosystem is strictly divided into four distinct components:

| Box | The Core Responsibility | Example |
|---|---|---|
| **1. Business System (BS)** | **WHAT** is actually true and what may be changed? Publishes Semantic + Schematic Public Contracts. | *"SKU 126BS has 10 units in stock. Uniqueness constraints pass."* |
| **2. AZM** | **WHAT** does this concept mean and **WHAT** schema exposes it? — stored as persistent knowledge, derived from the BS contracts. | *"A 'SKU' is a stock-keeping unit. It is exposed via `vw_stock_balances`. [Source: Inventory BS Semantic Contract v1.2]"* |
| **3. Brain Core** | **HOW** do we resolve/interpret the user's requirement? — reads AZM, never reads BS contracts directly. | *"The user's query translates to a SQL `SELECT` intent against `vw_stock_balances`."* |
| **4. Intelligence Domain** | **WHAT** does this mean for this particular business objective? | *"Given the inventory balances, this SKU represents a low-stock risk for the customer's query."* |

---

## 3. Exactly Two Public Contracts: Equilibrium & Decoupling

To ensure perfect decoupling, Business Systems (BS) publish **exactly two governed contracts**:

1. **Semantic Public Contract:** WHAT the business concepts mean, domain terminology, and semantic boundaries (authored/governed by the BS).
2. **Schematic Public Contract:** HOW those concepts are exposed/accessed via public views, APIs, or MCP schemas (authored/governed by the BS).

**AZM consumes and curates ONLY these two contracts.** It transforms these governed declarations into a **unified persistent knowledge model stored in AZM's own persistent database**. The contracts are source material. Operational records remain strictly inside the Business System.

---

## 4. Source-Declared Knowledge vs. AZM-Derived Knowledge

AZM's persistent knowledge falls into two distinct categories:

### 4.1 Source-Declared Knowledge
Knowledge that is explicitly declared in a BS Public Contract and faithfully normalized into AZM's knowledge model.

Example:
> Catalog BS Semantic Contract declares: *"SKU is the atomic sellable commercial unit."*
> → AZM creates a `Semantic Concept` node: `catalog.sku` with definition, aliases, provenance traceable to Catalog BS Semantic Contract v1.

### 4.2 AZM-Derived Ecosystem Knowledge
Knowledge that AZM derives by recognizing relationships *across* multiple BS contracts. No single BS contract states this relationship explicitly.

Example:
> Catalog BS declares `SKU`. Inventory BS declares `Stock Balance`.
> → AZM derives: `catalog.sku` *has* `inventory.stock_balance` (cross-BS relationship).
> → Provenance: *Derived by AZM ingestion engine from [Catalog BS Contract v1 + Inventory BS Contract v2]. Not explicitly declared by either BS.*

Both categories must be stored with full provenance. The provenance of derived knowledge must explicitly identify the derivation method and source contracts used.

---

## 5. Cross-Business-System Knowledge Integration

A primary architectural purpose of Azm is representing relationships *across* Business Systems. It is not merely a mirror of individual BS schemas.

For example, Azm represents ecosystem-level knowledge such as:
- **SKU** (Catalog BS concept)
  - *has* **Stock Balance** (Inventory BS concept)
  - *appears in* **Order Line** (Order BS concept)

This unified ontology is what allows Brain Core to orchestrate multi-domain workflows seamlessly.

---

## 6. Namespaces (Federated Knowledge) & Classification

Azm logically partitions its knowledge into domain namespaces. Namespaces are **not** all equivalent — they have different classification types:

| Namespace | Classification | Source Authority |
|---|---|---|
| **Catalog** | `AARAM_NATIVE` | Derived from Catalog BS Public Contracts |
| **Inventory** | `AARAM_NATIVE` | Derived from Inventory BS Public Contracts |
| **NDR (Logistics)** | `AARAM_NATIVE` | Derived from Order/Logistics BS Public Contracts |
| **ShopDeck** | `EXTERNAL_CHANNEL` | External channel reference — NOT Aaram-native semantics |

**Critical rule:** `EXTERNAL_CHANNEL` namespaces must never redefine or overwrite `AARAM_NATIVE` concepts. ShopDeck concepts may be stored in AZM as external mappings, but they cannot become canonical Aaram business meaning.

**Note on current legacy Python state:** The existing `src/azm/namespaces/shopdeck.py` treats ShopDeck as a peer namespace alongside Inventory and NDR in `GlobalAzmProvider`. This is a **legacy bootstrap limitation** — in the persistent AZM architecture, ShopDeck concepts will be stored as `EXTERNAL_CHANNEL` knowledge with structural differentiation from `AARAM_NATIVE` namespaces.

---

## 7. Architectural Evolution (The Roadmap)

Azm is an independent, persistent system on a clear evolutionary path.

- **Phase 1 (Legacy Bootstrap — Current State):** Azm defined declaratively in Python scripts (`src/azm/namespaces/`). These are NOT the architectural target — they are a transition scaffold only. They mix Aaram-native and external channel knowledge without structural differentiation.
- **Phase 2 (Persistent Ingestion):** Azm becomes a dynamic, persistent knowledge database that ingests the two Public Contracts from all Business Systems. Python namespaces are deprecated.
- **Phase 3 (FUTURE RESEARCH / LONG-TERM POSSIBILITY):** Azm serves as the foundational training data generator to fine-tune a local LLM. A potential long-term possibility is that the LLM absorbs the knowledge so deeply that a distinct Azm database becomes unnecessary. However, the persistent Azm architecture must remain valid regardless of LLM strategy shifts.

---

## 8. What AZM Persists vs. What AZM Does NOT Persist

| Persisted in AZM | NOT Persisted in AZM |
|---|---|
| Semantic Concept nodes (from BS Semantic Contracts) | Source contract files (markdown, SQL) |
| Schematic Reference nodes (view/API names and metadata) | Operational business records |
| Schematic Attribute nodes (fields, types, semantic annotations) | Transactional state |
| Semantic Relationships (within-BS and cross-BS) | Business execution logic |
| External/Channel Mapping nodes | BS-internal tables (not views) |
| Knowledge Provenance metadata | Second copies of BS truth |
| Knowledge Versions (history preserved) | |
| Lifecycle state (ACTIVE / DEPRECATED / ARCHIVED) | |
