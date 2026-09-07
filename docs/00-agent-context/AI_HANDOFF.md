# AI Handoff Document: AaramBooks Brain Core

**Last Updated:** 2026-09-02  
**Updated By:** Antigravity (AG)

---

## 1. Current System Status

### 1.1 RABTA Brain Core — CERTIFIED & FROZEN

All 11 RABTA phases are implemented, certified, and frozen.

### 1.2 NDR Intelligence Domain — CERTIFIED

NDR ID is fully implemented and certified including resolution engine, outcome evaluation, learning loop, and real integration validation. Boundary audit complete (`src/intelligence_domains/ndr/execution-boundary-audit.md`).

### 1.3 AZM Persistent Database — CERTIFIED & LIVE

The AZM persistent database (`azm_knowledge.db`, SQLite) is fully implemented and certified:

| Deliverable | File | Status |
|---|---|---|
| Physical DB schema | `src/azm/schema.sql` | ✅ Done |
| Universal ingestion engine | `src/azm/ingestion/universal_ingester.py` | ✅ Done |
| Generic contract parser | `src/azm/ingestion/contract_parser.py` | ✅ Done |
| Persistent DB provider | `src/azm/persistent_provider.py` | ✅ Done |
| Catalog semantic knowledge ingested | via `catalog-semantic-public-contract.md` | ✅ Done |
| Catalog schematic knowledge ingested | via `catalog-schematic-public-contract.md` | ✅ Done |
| AZM certification | `docs/03-azm-knowledge/07-azm-certification.md` | ✅ Certified |
| Contract grammar | `docs/03-azm-knowledge/08-azm-contract-grammar.md` | ✅ Done |
| Universal ingestion certification | `docs/03-azm-knowledge/09-azm-universal-contract-ingestion-certification.md` | ✅ Done |

**Legacy Python namespaces** (`src/azm/namespaces/inventory.py`, `src/azm/namespaces/ndr.py`) remain as deprecated bootstrap. `shopdeck.py` has been deleted. The Inventory namespace must NOT be migrated until Inventory BS publishes formal public contracts.

### 1.4 Phase 5B Architectural Boundaries — CERTIFIED

Typed multimodal and CEM read/verify boundaries are certified:
> `docs/03-intelligence-domains/architectural_boundary_certification_phase5b.md`

Key deliverables:
- `MultimodalQuery` contract — `src/shared/conversational_contracts.py`
- `BusinessStateVerificationRequest/Response` — `src/shared/evidence_request_contracts.py`
- `ContextExecutionResolver` — `src/shared/rabta_interfaces.py`

### 1.5 Catalog Intelligence Domain — PHASE 5B IMPLEMENTED

Phase 5B cognitive pipeline is fully implemented and all 23 tests pass:

| Component | File | Status |
|---|---|---|
| `CatalogDraft` (46 typed `DraftField`s) | `src/intelligence_domains/catalog_intelligence/models.py` | ✅ Done |
| `CatalogIntelligenceOrchestrator` | `src/intelligence_domains/catalog_intelligence/orchestrator.py` | ✅ Done |
| Cognitive pipeline (SABAQ → AZM → Qwen → Firewall → CEM) | orchestrator.py | ✅ Done |
| `CatalogCemAdapter` | `src/infrastructure/adapters/catalog_cem_adapter.py` | ✅ Done |
| `PostgresSabaqProvider` | `src/infrastructure/adapters/postgres_sabaq.py` | ✅ Done |
| All 23 cognitive/integration tests | `tests/intelligence_domains/catalog_intelligence/` | ✅ PASSING |

### 1.6 Business-Value Certification — FAILED GATE (Active Design Work)

The Phase 5B business-value certification FAILED the gate (only ~30% time reduction vs manual).  
Root cause: the Provenance Firewall naively erases all Qwen-proposed operational fields, forcing operators to retype dimensions, weights, and pricing — even when valid SABAQ historical precedent exists.

**Current state:** A revised Provenance Reuse Framework is in final design review. **No code changes are permitted until the framework design is approved.**

---

## 2. CRITICAL ARCHITECTURAL INVARIANT — 4-Box Architecture (FROZEN)

```
SABAQ             = Intelligence Training & Prior Data (advisory only, never authority)
AZM               = Semantic/Schematic Authority (from BS public contracts, not runtime)
CATALOG BS        = Current Operational Truth (accessed via CEM boundary only)
MEMORY PROVIDER   = Session/conversational state only
QWEN              = Inference engine only, never authority, never trusted for provenance
CATALOG ID        = Reasoning/Orchestration
CEM               = Business System Read/Write Boundary (typed contracts only)
```

**The Brain Core NEVER reads Business System contracts directly. All knowledge flows through AZM.**

---

## 3. Active Design Work: Provenance Firewall (Audit Mode — No Code Changes)

### Approved Principle
> **SABAQ_REUSED must NEVER be granted because Qwen outputs that tag.**  
> The application layer (Provenance Firewall) is the sole authority on provenance assignment.  
> Qwen may only propose *candidate values* and *evidence references*.

### Three Structural Corrections (Approved — Awaiting Final Design)

**Correction 1 — Scenario classification must be CEM-grounded, not Qwen-grounded:**
Scenarios A/B/C/D (restoration / family variant / new SKU / new family) may ONLY be determined after a `BusinessStateVerificationRequest` resolves the candidate `product_code` against the current Catalog BS. Qwen's unverified product_code proposal must never drive scenario classification.

**Correction 2 — Each reusable field needs its own explicit applicability rule:**  
"Same family + same size" is not sufficient proof for packaging dimensions. Every candidate reusable field must have a deterministic applicability rule that includes: applicable scenarios, exact matching keys, AZM bounds check, absence of conflicting business configuration, and a defined fallback (`UNKNOWN_REQUIRES_USER`).

**Correction 3 — Scenario A requires explicit historical identity:**  
Visual or descriptive similarity does NOT establish that a SKU is an exact historical restoration. Scenario A requires: explicit historical SKU identity supplied by the user, OR deterministic identity match against authoritative records.

### SABAQ_REUSED Definition (Approved)
> `SABAQ_REUSED` means: *"The application deterministically established that this exact historical value is applicable under an approved reuse rule."*  
> It does NOT mean: *"Qwen found a similar historical product."*

### Dependency Order (Approved)
```
Qwen (propose candidate + evidence reference)
  → CEM Verification (establish family relationship / scenario A/B/C/D)
  → SABAQ (retrieve historical precedent for verified family)
  → AZM (check bounds and categorical constraints)
  → Provenance Firewall (deterministic promotion decision)
```

---

## 4. Field Safety Classification (Approved)

| Field | Auto-Reuse Eligible? | Applicability Rule Summary |
|---|---|---|
| `packaging_length_cm` / `breadth` / `height` | Yes (Scenario B/C only) | Same `product_code` (CEM-verified) + same `size` + same `pack_configuration` + within AZM bounds |
| `packaging_weight_kg` | Yes (Scenario B/C only) | Same rules as dims — independently verified, not inherited from dims match |
| `mrp` | Conditionally (Scenario B/C only) | Same `product_code` (CEM-verified) + same `size` + AZM "Uniform Family Pricing" config active |
| `selling_price` | Never | Volatile marketing/discount truth — always `UNKNOWN_REQUIRES_USER` |
| `cost_price` | Never | Historical cost is not current operational cost — always `UNKNOWN_REQUIRES_USER` |
| `product_code` | Pattern only | SABAQ informs generation pattern; final identity requires CEM verification |
| `sku_id` | Pattern only | SABAQ informs generation pattern; final identity requires CEM verification |
| Descriptive fields (`product_name`, `description`, etc.) | Yes (`AI_PROPOSED` accepted) | Subject to AZM category constraints; operator confirmation required |

---

## 5. Open Work (In Priority Order)

| Item | Status |
|---|---|
| Final provenance reuse framework design (artifact panel) | ⏳ Awaiting user approval |
| Implement `evaluate_provenance_promotion()` in orchestrator | 🔒 Blocked on approval |
| Write provenance firewall unit tests | 🔒 Blocked on approval |
| Run REAL 10-SKU reproducible benchmark (not simulated) | 🔒 Blocked on approval |
| Inventory BS public contracts (for AZM migration of legacy namespace) | ❌ Not started |

---

## 6. Do NOT Do

- **Do NOT modify SABAQ, AZM, Rabta, CEM, or the four-box architecture** during the benchmark phase.
- **Do NOT let Qwen self-certify provenance** — the Firewall is the sole provenance authority.
- **Do NOT classify scenarios A/B/C/D from unverified Qwen output** — CEM verification is required first.
- **Do NOT assume same family + same size proves packaging dimensions** — each field has its own rule.
- **Do NOT automatically reuse historical pricing** — `cost_price` and `selling_price` are never auto-reusable.
- **Do NOT proceed to NDR or Customer Query implementation** until Catalog Phase 5B passes the business-value gate.
- **Do NOT collapse the 4-box architecture.**
- **Do NOT allow Brain Core to read BS Public Contracts directly.**
- **Do NOT treat the simulated 10-SKU benchmark as business-value evidence** — a real reproducible benchmark is required.

---

## 7. Key Artifacts Reference

| Artifact | Path |
|---|---|
| Phase 5B Boundary Certification | `docs/03-intelligence-domains/architectural_boundary_certification_phase5b.md` |
| AZM Architecture | `docs/03-azm-knowledge/` |
| AZM Contract Grammar | `docs/03-azm-knowledge/08-azm-contract-grammar.md` |
| SABAQ Architecture | `docs/04-sabaq/` |
| Business-Value Certification (FAIL) | `docs/04-sabaq/phase-5b-business-value-certification.md` |
| Catalog Business Rules | `business_systems/catalog/docs/03-catalog-business-rules.md` |
| Catalog Semantic Public Contract | `business_systems/catalog/public-contracts/catalog-semantic-public-contract.md` |
| Catalog Schematic Public Contract | `business_systems/catalog/public-contracts/catalog-schematic-public-contract.md` |
| Ecosystem Architecture | `docs/01-architecture/ecosystem-architecture.md` |
