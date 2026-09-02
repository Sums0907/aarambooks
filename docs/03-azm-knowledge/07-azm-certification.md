# Azm Architecture Certification

**Document Reference:** `docs/03-azm-knowledge/07-azm-certification.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Architectural Certification Checklist

This certification verifies that the Persistent Azm Architecture adheres to all ecosystem invariants and safely establishes the required 4-box boundaries.

- [x] **Four-box architecture:** Explicitly separates BS, AZM, Brain Core, and Intelligence Domains.
- [x] **Exactly two BS Public Contracts:** Clarifies that BSs expose only Semantic and Schematic contracts for knowledge.
- [x] **BS semantic authority:** BS owns canonical truth and semantic declarations.
- [x] **AZM independent existence:** Azm is the ecosystem's standalone persistent representation.
- [x] **AZM persistent knowledge representation:** It derives knowledge; it doesn't just store markdown text.
- [x] **AZM is not a contract archive.** Contracts are source material.
- [x] **AZM is not a BS mirror.** The DB represents knowledge, not transactional tables.
- [x] **AZM does not own operational truth.**
- [x] **Brain → AZM knowledge boundary:** Brain never directly reads BS contracts or reverse-engineers DDL.
- [x] **Knowledge vs operational-data separation:** Explicitly divided between Brain queries and Execution Machinery.
- [x] **Cross-BS knowledge capability:** Azm integrates concepts across Domains.
- [x] **Provenance and lineage:** Source Provenance is strictly separated from Azm Knowledge Identity.
- [x] **Versioning:** Knowledge is versioned; stale contracts are detectable.
- [x] **Catalog/ShopDeck semantic independence:** ShopDeck remains explicitly categorized as `EXTERNAL_CHANNEL_KNOWLEDGE`.
- [x] **Technology agnosticism:** PostgreSQL and LLMs are classified as future decisions/research, not architectural mandates.

## 2. Invariant Survival Tests

If this architecture is sound, it must survive the following scenarios:

**Q: If Catalog BS disappears tomorrow, does Azm's core architecture still exist?**
*Yes. Azm's ingestion engine, persistence model, and query boundary remain entirely intact. Only the Catalog namespace knowledge would be archived.*

**Q: If ShopDeck disappears tomorrow, do Aaram Catalog semantics still exist?**
*Yes. Catalog BS defined its own native semantics (`Product`, `SKU`), and Azm ingested them as Aaram canonical truth. The ShopDeck external mappings would simply be deprecated.*

**Q: If Catalog ID disappears tomorrow, does Azm still exist?**
*Yes. Intelligence Domains are downstream consumers. Their disappearance has zero impact on Azm's knowledge base.*

**Q: If Brain Core changes tomorrow, does Azm still exist?**
*Yes. Azm exposes a logical query boundary. If Brain is replaced, the new Brain simply queries the same Azm boundary.*

**Q: If a new Business System is introduced tomorrow, can it become a knowledge source without redesigning Azm?**
*Yes. It simply publishes a Semantic and Schematic Public Contract, and Azm's standard ingestion lifecycle absorbs it as a new namespace.*

---

**STATUS:** PERSISTENT AZM — ARCHITECTURE SPECIFICATION CERTIFIED
