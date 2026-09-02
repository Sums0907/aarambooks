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

## 3. AZM — Architecture CERTIFIED (Final Boundary Certification: commit `7b32376`)

**Current state of AZM:** `docs/03-azm-knowledge/` contains the complete 7-document architecture specification — fully certified after adversarial review.

### Key AZM Principles (Certified Invariants)

- **AZM IS:** The persistent, ecosystem-wide semantic & schematic knowledge repository with its own independent identity, knowledge model, and persistent database.
- **AZM IS NOT:** A contract repository, a BS mirror, a second Business System, a semantic authority, an operational data store, or a runtime reasoning engine.
- **BS is the semantic authority.** Business Systems declare authoritative domain meaning through Semantic Public Contracts. AZM represents (but does not define or override) that declared knowledge.
- **AZM is NOT Brain.** AZM performs limited, governed knowledge derivation at **ingestion time only**. Runtime reasoning belongs exclusively to Brain Core.
- **Source material:** Exactly **TWO** Business System Public Contracts feed into AZM (Semantic + Schematic).
- **Cross-BS purpose:** AZM's primary justification is representing relationships *across* Business Systems.
- **Python namespaces (`src/azm/namespaces/`):** **DEPRECATED legacy bootstrap.** The Persistent AZM DB is the target.

| AZM Document | Description |
|---|---|
| `01-azm-architecture.md` | 4-box architecture, AZM identity, source authority vs knowledge representation |
| `02-azm-knowledge-model.md` | Logical primitives: Concept, Relationship, SchematicRef, SchematicAttr, Provenance |
| `03-azm-knowledge-rules.md` | Hard invariants — AZM not semantic authority, ingestion-time derivation only, no BS bypass |
| `04-azm-ingestion-architecture.md` | Ingestion lifecycle, source-declared vs AZM-derived, versioning |
| `05-azm-query-boundary.md` | AZM is NOT Brain, Brain→AZM boundary, Intelligence Domain prohibition |
| `06-azm-persistence-model.md` | Persistence requirements, technology as future decision (not mandate) |
| `07-azm-certification.md` | Full certification checklist including AZM-not-Brain and AZM-not-semantic-authority |

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
- **Do NOT allow Brain Core to read BS Public Contracts directly** — all knowledge passes through AZM.
- **Do NOT allow ShopDeck fields to become Aaram-native Catalog concepts.**
- **Do NOT collapse the 4-box architecture** into fewer layers.
- **Do NOT treat the `src/azm/namespaces/*.py` files as permanent architectural truth** — they are legacy bootstrap, deprecated once persistent DB is live.
- **Do NOT make AZM perform runtime reasoning** — AZM ingests and stores; Brain reasons.
- **Do NOT finalise the NDR AZM namespace in this window** — that is the NDR window's responsibility.

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

---

## 8. Current Implementation State — AZM

> **This window's active focus is the AZM Persistent Database implementation.**

### What exists today (ALL legacy bootstrap — NOT the architectural target)

| File | Classification | Status |
|---|---|---|
| `src/azm/namespaces/inventory.py` | Legacy bootstrap — hardcoded Python dicts | No formal Inventory BS Public Contracts published yet |
| `src/azm/namespaces/ndr.py` | Legacy bootstrap — references `vw_shopdeck_*` views | No formal NDR/Logistics BS Schematic Contract yet |
| `src/azm/namespaces/shopdeck.py` | Legacy bootstrap — treated as peer namespace | ShopDeck is `EXTERNAL_CHANNEL`, not Aaram-native |
| `src/azm/provider.py` | Legacy bootstrap `GlobalAzmProvider` | Reads from Python dicts, not a persistent DB |

**No Intelligence Domain currently has proper semantic or schematic knowledge in AZM.** The Python namespace files are scaffold only.

### The NDR ID parallel window

NDR ID is actively being developed in a **separate conversation window**. Once this window delivers the AZM Persistent Database, the NDR window will be directed here to build the NDR AZM namespace.

**Do NOT attempt to finalise the NDR AZM namespace in this window.**

---

## 9. AZM Implementation Plan (Active)

A full implementation plan is available in the artifact:
> `implementation_plan.md` (visible in artifact panel)

**Summary of planned deliverables:**

| Deliverable | File | Status |
|---|---|---|
| Physical DB schema (10 tables) | `src/azm/schema.sql` | NOT STARTED |
| Python models for AZM primitives | `src/azm/models.py` | NOT STARTED |
| Persistent DB provider | `src/azm/provider.py` (updated) | NOT STARTED |
| Catalog static ingester | `src/azm/ingestion/catalog_ingester.py` | NOT STARTED |
| DB init + seed script | `src/azm/init_db.py` | NOT STARTED |
| Tests | `tests/azm/test_azm_persistent_provider.py` | NOT STARTED |

**Open decisions to resolve before starting:**
- Dev database: SQLite (zero-config) vs PostgreSQL (production-target)
- ORM vs raw SQL
- DB URL config location

---

## 10. Next Logical Steps (In Order)

1. **Resolve open implementation decisions** (DB engine for dev, ORM/raw SQL, config location).
2. **Implement AZM Persistent Database** — schema, models, PersistentAzmProvider, Catalog ingester, init script, tests.
3. **NDR window → NDR AZM namespace** — after DB exists, direct NDR window to publish formal contracts and ingest into AZM DB.
4. **Inventory BS Public Contracts** — Inventory BS must publish formal Semantic and Schematic contracts before legacy Python namespace can be migrated.
5. **Catalog ID Implementation** — Build Catalog ID using the established spec, consuming knowledge through AZM.
