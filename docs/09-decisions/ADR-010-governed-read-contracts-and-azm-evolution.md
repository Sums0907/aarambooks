# ADR 010: Public Read Contracts, Azm Federation, and Shared Text-to-SQL Architecture

## Status
Accepted (Phase 16 Architectural Consensus)

## Context
During diagnostic auditing of multi-intent inventory queries (e.g. BOM components, packing/shipment status), we identified that:
1. RABTA R-1/R-2/R-3 accurately extracted structured semantic requirements (`desired_outcome = "BOM components"`).
2. The legacy `InventoryCemAdapter` discarded structured data and relied on substring keyword matching with an `else: target_urn = "...balance"` fallback.
3. Micro-capability CEM registration for every read query created severe engineering friction and maintenance overhead.
4. Conversely, ungoverned Text-to-SQL causes hallucinations and security risks.

## Decision

We establish the **Canonical 4-Box Container Architecture & Public Read Contracts**:

### 1. Separation of Concerns & Container Responsibilities:
- **Container 1 (Brain Core):** Pure cognitive loop (RABTA), Model Gateway, and generic shared platform services including the **Shared Text-to-SQL Engine** and AST safety gate. 100% schema-blind and domain-agnostic.
- **Container 2 (Intelligence Domains):** Domain reasoning specialists (Inventory ID, NDR ID, CRM ID). Extracts domain entities, queries Azm for schemas, calls Brain Core's shared Text-to-SQL engine, and interprets returned evidence (R-8).
- **Container 3 (Global Azm):** Ecosystem-wide semantic ontology. Stores business terms, aliases, and public schema view definitions across namespaces (`inventory.*`, `ndr.*`). Accumulates training pairs for fine-tuning open-weight models (Qwen). Pure declarative data; zero I/O.
- **Container 4 (Business Systems):** Autonomous operational sources of truth (PostgreSQL on Port 5433). Publishes stable public SQL views (`vw_*`) and executes transactional mutations behind strict CEM nonces.

### 2. The Execution Split:
- **CEM:** Reserved strictly for transactional mutations/actions (`intent == ACTION`) requiring nonces and two-phase verification.
- **Read Substrate:** Dynamic, schema-grounded Text-to-SQL powered by Qwen 7B for all operational reads (`intent == RETRIEVE | CALCULATE`).

---

## Architecture Diagrams

### 1. The Canonical 4-Box Container Architecture
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 📦 CONTAINER 1: BRAIN CORE                                                             │
│ (The Cognitive Engine & Shared AI Machinery)                                           │
│                                                                                        │
│  • RABTA Cognitive Loop (R-1 to R-10)                                                  │
│  • Shared Text-to-SQL Engine (Qwen prompt, AST safety gate, read-only DB runner)        │
│  • Memory & Decision Engine (R-9 Nonces, R-10 Session Context)                         │
│  • Model Gateway (LiteLLM / vLLM / Gemini proxy)                                       │
│                                                                                        │
│  🚫 STRICT INVARIANT: 100% Schema-Blind & Domain-Agnostic (Zero mentions of SKU/NDR).   │
└───────────────────┬────────────────────────────────────────────────▲───────────────────┘
                    │                                                │
                    │ Calls Domain Specialist                        │ Returns Final Answer
                    ▼                                                │
┌────────────────────────────────────────────────────────────────────┴───────────────────┐
│ 📦 CONTAINER 2: INTELLIGENCE DOMAINS (IDs)                                             │
│ (The Domain Specialists: Inventory ID, NDR ID, CRM ID)                                │
│                                                                                        │
│  • Extracts Domain Entities (e.g. SKU, Vendor ID)                                     │
│  • Performs Domain Math (e.g. Available Stock = On Hand - Reserved)                    │
│  • Interprets Raw Facts into Business Answers (R-8)                                    │
│                                                                                        │
│  🚫 STRICT INVARIANT: Never hardcodes schemas; reads them from Azm.                   │
└──────────────┬───────────────────────────────────────────────▲─────────────────────────┘
               │                                               │
               │ 1. Gets Schema & Vocab                        │ 2. Sends SQL to Execute
               ▼                                               ▼
┌──────────────────────────────────────────────┐ ┌────────────────────────────────────────┐
│ 📦 CONTAINER 3: GLOBAL AZM                   │ │ 📦 CONTAINER 4: BUSINESS SYSTEMS       │
│ (The Semantic Ontology & Training Vault)     │ │ (The Independent Sources of Truth)     │
│                                              │ │                                        │
│  • Namespaced Business Terms (Aliases/Vocab) │ │  • PostgreSQL Database & Raw Tables    │
│  • Synced Public Read View Schemas (vw_*)    │ │  • Published Public Read Views (vw_*)  │
│  • Certified Business Policies & Guardrails  │ │  • Transactional CEM (Ledger Mutations)│
│  • Training Trajectory Flywheel              │ │                                        │
│                                              │ │  🚫 STRICT INVARIANT: Fully autonomous.│
│  🚫 STRICT INVARIANT: Pure declarative data. │ │     Knows nothing about Brain Core.    │
│     Never executes code or runs queries.     │ │                                        │
└──────────────────────────────────────────────┘ └────────────────────────────────────────┘
```

### 2. End-to-End Read Substrate Lifecycle
```
[ User Query ] ──► [ 1. Brain Core (RABTA) ]
                         │
                         ▼ (Delegates to the Domain Specialist)
┌─────────────────────────────────────────────────────────────┐
│                 INTELLIGENCE DOMAIN (ID)                    │
│                                                             │
│  Step 2: Calls Azm to get the domain's Public Schema        │
│          & business aliases.                                │
│                                                             │
│  Step 3: Prompts Qwen via Brain Core's Text-to-SQL Engine   │
│          ➔ Generates the SQL query.                         │
│                                                             │
│  Step 4: Passes SQL through the AST Safety Gate             │
│          ➔ Enforces `SELECT` only.                          │
│                                                             │
│  Step 5: Sends verified SQL over Gateway/Adapter            │
│          to the Business System.                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  BUSINESS SYSTEM (PostgreSQL)                               │
│  - Executes SQL on `vw_*` and returns raw rows/data.        │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 INTELLIGENCE DOMAIN (ID)                    │
│                                                             │
│  Step 6: Receives raw data, performs domain reasoning,      │
│          checks safety thresholds & wastage calculations.   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
[ 7. Brain Core (RABTA) ] ──► Updates memory (R-10) & delivers answer to User
```

### 3. The Golden Middle Ground (Public Read Contracts)
```
      THE TWO FLAWED EXTREMES                                  THE GOLDEN MIDDLE GROUND
                                                            
 ┌──────────────────────────────────┐                     ┌──────────────────────────────────┐
 │ Extreme 1: Hyper-Rigid CEM       │                     │ 🌟 PUBLIC READ CONTRACTS         │
 │ - Micro-capabilities for every   │                     │    (The Golden Middle Ground)    │
 │   single query (BOM, packing...) │                     │                                  │
 │ - Result: Engineering paralysis, │                     │ - Business System publishes      │
 │   hardcoded keyword hacks        │                     │   clean, stable SQL Views.       │
 └──────────────────────────────────┘                     │ - Azm ingests view schemas.      │
                                         VS               │ - Qwen generates precise,        │
 ┌──────────────────────────────────┐                     │   dynamic `SELECT` queries.      │
 │ Extreme 2: Ungoverned LLM        │                     │ - Zero Hallucinations,           │
 │ - Zero domain/schema grounding   │                     │   Zero Rigidity,                 │
 │ - Result: Hallucinations, broken │                     │   100% Decoupled.                │
 │   joins, wrong business numbers  │                     └──────────────────────────────────┘
 └──────────────────────────────────┘                     
```

## Consequences
- Eliminates the silent stock-balance fallback bug permanently.
- Unlocks arbitrary operational read queries (BOM, Packing, Suppliers, Jobwork).
- Zero code duplication across domains: Text-to-SQL is a shared Brain Core platform service.
- Preserves full schema decoupling between Business Systems and Brain Core.
- Builds high-quality training pairs in Azm for fine-tuning local open-weight models (Qwen).
