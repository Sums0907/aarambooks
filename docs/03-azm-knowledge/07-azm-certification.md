# Azm Architecture Certification

**Document Reference:** `docs/03-azm-knowledge/07-azm-certification.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Architectural Certification Checklist

This certification verifies that the Persistent Azm Architecture adheres to all ecosystem invariants and safely establishes the required 4-box boundaries. This checklist was evaluated during the Final Forensic Architectural Review (September 2026).

### Four-Box Architecture
- [x] **Four-box architecture:** Explicitly separates BS, AZM, Brain Core, and Intelligence Domains without collapsing.
- [x] **Exactly two BS Public Contracts:** BSs expose only Semantic and Schematic contracts for knowledge ingestion.
- [x] **BS semantic authority:** BS owns canonical truth and semantic declarations. AZM owns the persistent representation derived from those declarations.

### AZM Identity & Independence
- [x] **AZM independent existence:** Azm is the ecosystem's standalone persistent knowledge representation.
- [x] **AZM persistent knowledge representation:** It derives knowledge; it doesn't just store source contracts or markdown text.
- [x] **AZM is NOT the semantic authority.** Business Systems declare authoritative domain meaning through Semantic Public Contracts. AZM persists a normalized, queryable representation of that declared knowledge. AZM may not independently redefine, override, or contradict BS-declared meaning. SOURCE AUTHORITY (BS) ≠ KNOWLEDGE REPRESENTATION (AZM).
- [x] **AZM is not a contract archive.** Contracts are source material. AZM stores derived knowledge nodes, not contract files.
- [x] **AZM is not a BS mirror.** The knowledge model represents logical primitives, not transactional BS tables.
- [x] **AZM does not own operational truth.**
- [x] **AZM is NOT Brain.** AZM prepares and maintains persistent knowledge through limited, governed derivation at ingestion time. AZM does NOT perform runtime reasoning or inference. Runtime reasoning belongs exclusively to Brain Core.

### Semantic Knowledge
- [x] **AZM persists semantic knowledge as first-class nodes:** Semantic Concepts, Definitions, Aliases, Relationships.
- [x] **Source-declared knowledge is distinguished from AZM-derived knowledge:** Both categories are stored; their provenance records differ explicitly.
- [x] **AZM-derived cross-BS relationships have explainable provenance:** A derived relationship must answer "Why does AZM believe this relationship exists?"
- [x] **Intelligence Domains do not create semantic shadow systems:** IDs consume knowledge through the architecture.

### Schematic Knowledge
- [x] **AZM persists schematic knowledge as first-class nodes:** Schematic References (views/APIs), Schematic Attributes (fields), Attribute Mappings (field ↔ concept links).
- [x] **Schematic knowledge is more than a view name list:** AZM must persist field-level (column-level) knowledge including data types, descriptions, and semantic concept mappings.
- [x] **AZM can answer field-level schematic questions:** "Which field in `vw_catalog_skus` represents the selling price?" is answerable from AZM knowledge without inspecting the original contract.

### Brain Boundary
- [x] **Brain → AZM knowledge boundary:** Brain never directly reads BS contracts or reverse-engineers DDL to learn meaning.
- [x] **Intelligence Domain → AZM boundary:** Intelligence Domains also may not directly read BS contracts to reconstruct semantics. Knowledge flows through AZM.
- [x] **Knowledge vs operational-data separation:** Knowledge retrieval (Brain → AZM) is explicitly divided from operational data retrieval (Execution Machinery → Business System).
- [x] **AZM never becomes operational-data storage:** AZM does not cache current SKU stock counts, order records, or other transactional data.

### Provenance & Versioning
- [x] **Provenance and lineage:** Source Provenance is strictly separated from Azm Knowledge Identity.
- [x] **Dual provenance model:** Source-Declared knowledge traces to BS → Contract → Element. AZM-Derived knowledge traces to [Contract A + Contract B] → Derivation Method.
- [x] **Versioning:** Knowledge is versioned; stale contracts are detectable. Historical knowledge is archived, not deleted.

### Catalog / ShopDeck Boundary
- [x] **Catalog remains Aaram-native:** Catalog semantics are sourced from Catalog BS Public Contracts, not from ShopDeck.
- [x] **Catalog/ShopDeck semantic independence:** ShopDeck remains explicitly categorized as `EXTERNAL_CHANNEL_KNOWLEDGE`. Its concepts cannot overwrite `AARAM_NATIVE` concepts.
- [x] **Namespace classification is structurally explicit:** AZM namespaces carry an explicit classification (`AARAM_NATIVE` vs `EXTERNAL_CHANNEL`), not just a string label.

### Legacy State & Technology
- [x] **Legacy Python namespaces are clearly transitional:** `src/azm/namespaces/*.py` are classified as Phase 1 Bootstrap — they will be deprecated when the persistent DB ingestion engine is live.
- [x] **Technology agnosticism:** PostgreSQL and LLMs are classified as future decisions/research, not architectural mandates.
- [x] **All seven AZM documents are mutually consistent.**

---

## 2. Invariant Survival Tests

**Q: If Catalog BS disappears tomorrow, does Azm's core architecture still exist?**
*Yes. Azm's ingestion engine, persistence model, and query boundary remain entirely intact. Only the Catalog namespace knowledge would be archived.*

**Q: If ShopDeck disappears tomorrow, do Aaram Catalog semantics still exist?**
*Yes. Catalog BS defined its own native semantics (`Product`, `SKU`), and Azm ingested them as Aaram canonical truth. The ShopDeck External Mapping nodes would simply be marked DEPRECATED.*

**Q: If Catalog ID disappears tomorrow, does Azm still exist?**
*Yes. Intelligence Domains are downstream consumers. Their disappearance has zero impact on Azm's knowledge base.*

**Q: If Brain Core changes tomorrow, does Azm still exist?**
*Yes. Azm exposes a logical query boundary. If Brain is replaced, the new Brain simply queries the same Azm boundary.*

**Q: If a new Business System is introduced tomorrow, can it become a knowledge source without redesigning Azm?**
*Yes. It simply publishes a Semantic and Schematic Public Contract, and Azm's standard ingestion lifecycle absorbs it as a new namespace.*

**Q: If someone asks "Why does AZM believe SKU has Stock Balance?", can AZM answer?**
*Yes. The derived relationship carries derivation provenance: "Derived by AZM ingestion engine from [Catalog BS Semantic Contract v1 + Inventory BS Semantic Contract v1], by cross-domain join analysis."*

**Q: Can Amazon or Flipkart be added as channels without invalidating Catalog semantics?**
*Yes. They would be ingested as additional `EXTERNAL_CHANNEL` namespace mappings. Aaram-native `AARAM_NATIVE` Catalog concepts remain unchanged.*

---

## 3. Open Gaps (Not Blocking Certification)

The following gaps are documented but do not prevent architectural certification. They must be resolved before implementation of the persistent AZM database.

| Gap | Document | Status |
|---|---|---|
| Conflict resolution protocol when two BSes legitimately differ on a shared boundary concept | `04-azm-ingestion-architecture.md §3.5` | OPEN GAP / DECISION REQUIRED |
| Exact query API/protocol for Brain Core → AZM (GraphQL, REST, Python interface) | `05-azm-query-boundary.md §3` | OPEN GAP / DECISION REQUIRED |
| Physical database implementation details (tables, columns, indexes) | `06-azm-persistence-model.md §2` | OPEN GAP / DECISION REQUIRED |
| Inventory BS has no formal Semantic or Schematic Public Contract yet (`src/azm/namespaces/inventory.py` is legacy bootstrap only) | `README.md §7` | OPEN GAP — must be resolved before Inventory namespace is ingested into persistent AZM |
| NDR schematic knowledge currently references ShopDeck operational views (`vw_shopdeck_*`) — these are transitional bootstrap views, not a formally governed BS Schematic Contract | `README.md §6` | OPEN GAP — Inventory/Logistics BS must publish formal contracts before NDR namespace migrates to persistent AZM |

---

**STATUS: AZM ARCHITECTURE — CERTIFIED**

*Final Boundary Certification Pass, September 2026.*
*Certification scope: Architectural documentation completeness, internal consistency, and boundary invariant enforcement.*
*Key invariants confirmed: (1) BS is semantic authority; (2) AZM is knowledge representation layer; (3) AZM performs ingestion-time derivation only — not runtime reasoning; (4) Brain reads AZM, not BS contracts; (5) Intelligence Domains do not bypass AZM; (6) Catalog is Aaram-native; (7) ShopDeck is EXTERNAL_CHANNEL.*
*Implementation (persistent DB, ingestion engine, Brain API) remains pending — see Open Gaps above.*
