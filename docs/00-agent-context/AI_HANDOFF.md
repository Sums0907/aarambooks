# AI Handoff Document: AaramBooks Brain Core

**Last Updated:** 2026-09-02
**Updated By:** Antigravity (AG)

---

## 1. Current System Status

### 1.1 RABTA Brain Core — CERTIFIED & FROZEN

All 11 RABTA phases are implemented, certified, and frozen:

| Phase | Description | Status |
|---|---|---|
| R-2 | Context Extraction | ✅ Implemented |
| R-3 | Requirement Classification | ✅ Implemented |
| R-4 | Business Discovery (CEM) | ✅ Implemented |
| R-5 | Entity Resolution (CEM) | ✅ Implemented |
| R-6 | Orchestration / Refinement Loop | ✅ Implemented (max 2-pass bounded) |
| R-7 | Business Execution (CEM) | ✅ Implemented |
| R-8 | Conversational Interpretation | ✅ Implemented (deterministic, LLM-free) |
| R-9 | Decision & Action Safety | ✅ Implemented |
| R-10 | Memory Continuity | ✅ Implemented |
| R-11 | Ecosystem Communication | ✅ Implemented |

### 1.2 NDR Intelligence Domain — CERTIFIED

NDR ID is fully implemented and certified including:
- Resolution engine
- Outcome evaluation & learning loop
- Real integration validation (including `vw_shopdeck_shipment_ndr_reports` execution)
- Boundary audit complete (see `execution-boundary-audit.md`)

### 1.3 Catalog Intelligence Domain — SPECIFICATION COMPLETE, IMPLEMENTATION PENDING

Catalog ID specification is fully documented (7-document suite) in `docs/03-intelligence-domains/catalog-intelligence/`. **No Catalog ID code has been implemented yet.**

---

## 2. CRITICAL ARCHITECTURAL INVARIANT — 4-Box Architecture

The ecosystem is governed by a strict 4-box architecture. **This must never be collapsed:**

```
BUSINESS SYSTEM
    │
    │  Semantic Public Contract (what concepts mean)
    │  Schematic Public Contract (how concepts are exposed)
    ▼
   AZM (Aaram Zameer)
    │
    │  Persistent semantic/schematic knowledge
    ▼
 BRAIN CORE
    │
    │  Reasoning / Orchestration
    ▼
INTELLIGENCE DOMAIN
```

### The Knowledge Flow Rule

> **Brain Core NEVER reads Business System Public Contracts directly.**
> Brain reads knowledge **exclusively through AZM**.

---

## 3. AZM — Persistent Architecture Specification CERTIFIED

**Current state of AZM:** `docs/03-azm-knowledge/` contains the complete 7-document architecture specification.

### Key AZM Principles

- **AZM IS:** The persistent, ecosystem-wide semantic & schematic knowledge repository. It has its own independent identity, knowledge model, and persistent database.
- **AZM IS NOT:** A contract repository, a BS mirror, a second Business System, or an operational data store.
- **Source material:** Exactly **TWO** Business System Public Contracts feed into AZM (Semantic + Schematic). Operational records stay in the BS.
- **Cross-BS purpose:** AZM's primary justification is its ability to represent relationships *across* Business Systems (e.g., Catalog `SKU` *has* Inventory `Stock Balance`).
- **Python namespaces (`src/azm/namespaces/`):** Classified as **legacy/bootstrap only**. Target is the Persistent AZM Database.

| AZM Document | Description |
|---|---|
| `01-azm-architecture.md` | 4-box architecture, AZM identity, Catalog/ShopDeck boundary |
| `02-azm-knowledge-model.md` | Logical primitives: Concept, Relationship, Schema, Provenance |
| `03-azm-knowledge-rules.md` | Hard invariants — no contract mirroring, no BS bypass |
| `04-azm-ingestion-architecture.md` | Ingestion lifecycle, versioning, conflict handling |
| `05-azm-query-boundary.md` | Knowledge vs operational retrieval, Brain→AZM boundary |
| `06-azm-persistence-model.md` | Persistence requirements, technology decisions (open gaps) |
| `07-azm-certification.md` | Full certification checklist & survival tests |

---

## 4. Catalog Business System — PUBLIC CONTRACTS ESTABLISHED

The Catalog BS (`business_systems/catalog/`) is a certified, frozen operational system.

### Catalog Public Contracts

| Contract | Location |
|---|---|
| **Semantic Public Contract** | `business_systems/catalog/public-contracts/catalog-semantic-public-contract.md` |
| **Schematic Public Contract** | `business_systems/catalog/public_views.sql` |

### Critical Catalog Rules

- Catalog BS owns **Aaram-native** Catalog semantics (`Product`, `SKU`).
- **ShopDeck is an external commerce channel.** Its fields (`commerce_available_qty`, `customer_sku_short_id`) are channel-specific and must NOT redefine Aaram-native Catalog concepts.
- The architecture must survive: *"ShopDeck disappears tomorrow."* Aaram Catalog semantics remain valid.

---

## 5. Open Gaps / Decision Required

| Gap | Location |
|---|---|
| AZM physical DB implementation (tables, indexes) | `06-azm-persistence-model.md` |
| AZM ingestion engine implementation | `04-azm-ingestion-architecture.md` |
| Brain→AZM exact query API/protocol | `05-azm-query-boundary.md` |
| Conflict resolution when two BS declarations differ on a shared concept | `04-azm-ingestion-architecture.md` |
| Catalog ID implementation | `docs/03-intelligence-domains/catalog-intelligence/` |
| Inventory BS legacy Python namespace (`src/azm/namespaces/inventory.py`) must be migrated to proper BS Public Contracts | `src/azm/` |

---

## 6. Do NOT Do

- **Do NOT modify Catalog BS** code, DDL, schema, service, or tests.
- **Do NOT implement Catalog ID** without explicit instruction.
- **Do NOT implement AZM persistence** (DB tables/code) without explicit instruction.
- **Do NOT allow Brain Core to read BS Public Contracts directly** — all knowledge passes through AZM.
- **Do NOT allow ShopDeck fields to become Aaram-native Catalog concepts.**
- **Do NOT collapse the 4-box architecture** into fewer layers.
- **Do NOT treat the `src/azm/namespaces/*.py` files as permanent architectural truth** — they are legacy bootstrap only.

---

## 7. Key Artifacts Reference

| Artifact | Path |
|---|---|
| RABTA Brain Core Architecture | `docs/02-brain-core/` |
| NDR Intelligence Domain | `docs/03-intelligence-domains/ndr-intelligence/` |
| Catalog Intelligence Domain (spec) | `docs/03-intelligence-domains/catalog-intelligence/` |
| AZM Architecture Specification | `docs/03-azm-knowledge/` |
| Catalog Semantic Public Contract | `business_systems/catalog/public-contracts/catalog-semantic-public-contract.md` |
| Catalog Schematic Public Contract | `business_systems/catalog/public_views.sql` |
| Ecosystem Architecture | `docs/01-architecture/ecosystem-architecture.md` |
| NDR Boundary Audit | `src/intelligence_domains/ndr/execution-boundary-audit.md` |

---

## 8. Next Logical Steps

1. **AZM Persistent Database** — Implement the physical Azm DB using the `06-azm-persistence-model.md` spec.
2. **AZM Ingestion Engine** — Implement ingestion from BS Public Contracts into the Azm DB.
3. **Catalog AZM Namespace** — Once AZM DB is live, ingest the Catalog BS Public Contracts to create the first Azm Catalog knowledge namespace.
4. **Catalog ID Implementation** — Build Catalog ID using the established spec and consuming knowledge through AZM.
