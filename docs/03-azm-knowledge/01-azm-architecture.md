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

Azm exists because Business Systems own operational truth, but the AI Brain needs a governed, unified, and persistent map of what that truth *means* and *how it is exposed*. Azm provides that map.

---

## 2. The 4-Box Ecosystem Architecture

The architecture enforces strict boundaries between four distinct ecosystem components:

1. **BUSINESS SYSTEMS (BS)**
   - **Role:** The masters of operational truth. 
   - **Responsibility:** They execute transactions, enforce validation, own canonical identities, and publish governed Semantic and Schematic Public Contracts.

2. **AZM**
   - **Role:** The ecosystem knowledge representation.
   - **Responsibility:** Ingests BS Public Contracts and derives persistent semantic and schematic knowledge into its own distinct knowledge model. 

3. **BRAIN CORE**
   - **Role:** The reasoning and orchestration engine.
   - **Responsibility:** Performs generalized intelligence tasks. 
   - **Invariant:** Brain Core **NEVER** directly reads Business System Public Contracts. It reads knowledge exclusively through Azm.

4. **INTELLIGENCE DOMAINS (ID)**
   - **Role:** The application of intelligence to specific objectives (e.g., Catalog ID).
   - **Responsibility:** Consumes the Brain + Azm knowledge to perform domain-specific reasoning (like parsing a supplier invoice into a proposed Catalog SKU).

---

## 3. Boundary Definitions

### Azm vs. Business System
- **Operational Sovereignty:** Business Systems are the sole authority for operational truth. Azm does not invent, override, or duplicate operational records.
- **Contract Ownership:** Business Systems own their Public Contracts. Azm ingests them. 

### Azm vs. Public Contracts
- **Ingestion != Copying:** Azm does not simply store a text copy of a contract. It reads the contract, extracts the semantic definitions and schematic mappings, and constructs its own normalized, persistent knowledge entities.

### Azm vs. Brain Core
- **The Access Invariant:** Brain relies entirely on Azm for its understanding of the ecosystem. If Azm does not know a concept, Brain cannot reason about it.

### Semantic vs. Schematic Knowledge
- **Semantic Knowledge:** Defines *meaning* (e.g., "A SKU is the atomic sellable unit").
- **Schematic Knowledge:** Defines *exposure* (e.g., "The SKU concept is exposed via the `vw_catalog_skus` SQL view with fields X, Y, Z").

---

## 4. The Source / Provenance Model
Azm must always know *where* its knowledge came from. Every concept in Azm traces back to:
- The authoritative Business System.
- The specific Public Contract declaration.
- The temporal point of ingestion.

This prevents "knowledge drift" and ensures Azm never hallucinates authoritative meaning.

---

## 5. The Catalog / ShopDeck Boundary Example
This architecture protects Aaram-native semantics from external channel leakage:
- **ShopDeck** is an external commerce channel. Its schema (e.g., `commerce_available_qty`, `customer_sku_short_id`) represents channel state, not core Aaram truth.
- **Aaram Catalog BS** defines the true, channel-agnostic meaning of a `Product` and `SKU`.
- **Azm** ingests the Catalog BS contract to learn the Aaram-native semantics. It treats ShopDeck merely as an external mapping reference, ensuring that if ShopDeck disappears tomorrow, Aaram's core semantic knowledge remains intact.
