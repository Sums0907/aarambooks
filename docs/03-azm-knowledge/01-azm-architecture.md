# Azm Persistent Architecture Specification

**Document Reference:** `docs/03-azm-knowledge/01-azm-architecture.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Purpose of Azm

**AZM IS:** The persistent, ecosystem-wide semantic and schematic knowledge repository of AaramBooks. It has its own independent existence, its own knowledge model, and its own persistent database.

**AZM IS NOT:**
- A contract repository or Markdown/SQL archive.
- A mirror of Business System schemas.
- A second Business System.
- A repository of operational records or transactional truth.
- A collection of Python namespaces (the legacy bootstrap state).
- The owner of canonical business truth (the Business System owns this).

Azm exists because Business Systems own operational truth, but the AI Brain needs a governed, unified, and persistent map of what that truth *means*, how it connects across domains, and *how it is exposed*. Azm provides that unified map.

---

## 2. The 4-Box Ecosystem Architecture

The architecture enforces strict boundaries between four distinct ecosystem components. They must not be collapsed:

1. **BUSINESS SYSTEMS (BS)**
   - **Role:** The masters of operational truth. 
   - **Responsibility:** They execute transactions, enforce validation, own canonical identities, and publish exactly two governed contracts: the Semantic Public Contract and the Schematic Public Contract.

2. **AZM**
   - **Role:** The ecosystem knowledge representation.
   - **Responsibility:** Ingests the two BS Public Contracts and derives persistent semantic and schematic knowledge into its own distinct knowledge model. It enables cross-BS knowledge integration.

3. **BRAIN CORE**
   - **Role:** The reasoning and orchestration engine.
   - **Responsibility:** Performs generalized intelligence tasks. 
   - **Invariant:** Brain Core **NEVER** directly reads Business System Public Contracts or DDL to learn meaning. It reads knowledge exclusively through Azm.

4. **INTELLIGENCE DOMAINS (ID)**
   - **Role:** The application of intelligence to specific objectives (e.g., Catalog ID).
   - **Responsibility:** Consumes the Brain + Azm knowledge to perform domain-specific reasoning. An ID never bypasses Azm to become a shadow semantic master.

---

## 3. Boundary Definitions

### Azm vs. Business System
- **Operational Sovereignty:** Business Systems are the sole authority for operational truth. Azm does not invent, override, or duplicate operational records.
- **Semantic Authority:** Business Systems are the sole authority for authoritative domain semantic declarations. AZM owns the persistent ecosystem *representation* of that declared knowledge — it does not redefine or override BS-declared meaning.

### Azm vs. Public Contracts
- **Ingestion != Copying:** Azm is not a contract archive. Contracts are source material. Azm reads the contract, extracts meaning, and constructs normalized, persistent knowledge entities inside its own database. Brain reads Azm, not the contracts.

### Azm vs. Brain Core
- **Knowledge Retrieval vs Operational Retrieval:** Brain queries Azm for *Knowledge* ("What is a SKU and how is it exposed?"). Brain/Execution machinery queries authorized Business System access mechanisms for *Operational Reality* ("What is the current stock of SKU 126BS?").

### Semantic vs. Schematic Knowledge
- **Semantic Knowledge:** Defines *meaning* (e.g., "A SKU is the atomic sellable unit").
- **Schematic Knowledge:** Defines *exposure* (e.g., "The SKU concept is exposed via the `vw_catalog_skus` SQL view").

---

## 4. The Source / Provenance Model
Azm must always know *where* its knowledge came from. Every concept in Azm traces back through strict lineage:
1. Business System
2. Public Contract
3. Contract version/hash
4. Specific declaration
5. Azm ingestion run
6. Azm knowledge version

This prevents "knowledge drift" and distinguishes *Source Provenance* from *Azm Knowledge Identity*.

---

## 5. The Catalog / ShopDeck Boundary Example
This architecture protects Aaram-native semantics from external channel leakage:
- **ShopDeck** is an external commerce channel. Its schema (e.g., `commerce_available_qty`, `customer_sku_short_id`) represents channel state, not core Aaram truth.
- **Aaram Catalog BS** owns the true, channel-agnostic meaning of a `Product` and `SKU`.
- **Azm** ingests the Catalog BS contract to learn the Aaram-native semantics. It treats ShopDeck merely as an external mapping reference, ensuring that if ShopDeck disappears tomorrow, Aaram's core semantic knowledge remains completely valid.

---

## 6. Source-Declared Knowledge vs. AZM-Derived Knowledge

AZM's persistent knowledge is explicitly classified into two categories, both of which must carry distinct provenance:

**Source-Declared Knowledge:** Directly and faithfully extracted from an explicit declaration in a BS Public Contract.
> Example: Catalog BS Semantic Contract declares `SKU = "atomic sellable unit"`. AZM persists this as a Semantic Concept node with provenance pointing to Catalog BS Semantic Contract v1.

**AZM-Derived Ecosystem Knowledge:** During the ingestion process, AZM performs limited, governed knowledge derivation by recognizing relationships across BS contracts. No single BS explicitly states the full relationship. **This derivation happens at ingestion time, not at Brain query time.** AZM stores the derived relationship as a persistent knowledge node with explicit derivation provenance. AZM does not perform runtime reasoning — that is Brain Core's role.
> Example: No contract explicitly says "SKU has Stock Balance." During ingestion, AZM recognizes that Catalog BS exposes `sku_id` and Inventory BS exposes `sku` in `vw_stock_balances`. AZM creates a persistent Semantic Relationship node with derivation provenance: "[Catalog BS Contract v1 + Inventory BS Contract v1] → cross-domain join analysis, ingestion run #N."

Derived relationships must be able to answer: *"Why does AZM believe this relationship exists?"*

---

## 7. Known Transitional Gaps in Current Legacy State

The following known gaps exist in the current Phase 1 legacy Python implementation and must be resolved before the persistent AZM database is implemented:

1. **Inventory BS has no formal Public Contracts yet.** `src/azm/namespaces/inventory.py` is a legacy bootstrap file that directly defines concepts and views. It is NOT derived from a published Inventory BS Semantic or Schematic Public Contract. Before the Inventory namespace is migrated to the persistent AZM DB, Inventory BS must publish formal Semantic and Schematic Public Contracts.

2. **NDR schematic knowledge references ShopDeck operational views.** `src/azm/namespaces/ndr.py` defines `NDR_PUBLIC_VIEWS` pointing to `vw_shopdeck_*` views. These are operational view names from ShopDeck's infrastructure — they are transitional bootstrap references, not a formally governed Logistics/Orders BS Schematic Public Contract. Before the NDR namespace migrates to the persistent AZM DB, a formal NDR/Logistics BS Schematic Public Contract must be established.

3. **ShopDeck namespace is treated as peer to Aaram-native namespaces in legacy code.** `src/azm/provider.py` registers `shopdeck` alongside `inventory` and `ndr` without structural differentiation. In the persistent AZM architecture, ShopDeck is classified as `EXTERNAL_CHANNEL` — structurally distinct from `AARAM_NATIVE` namespaces.
