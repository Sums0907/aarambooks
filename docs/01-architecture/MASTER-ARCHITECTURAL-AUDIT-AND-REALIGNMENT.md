# Master Architectural Audit, Systemic Findings, and Foundational Realignment

**Document Identifier:** `ARCH-AUDIT-2026-08-31`  
**Status:** Canonical Reference & Architectural Baseline  
**Classification:** Foundational Architecture & Boundary Grounding  
**Authoritative Scope:** Brain Core (RABTA), Azm Knowledge Federation, Intelligence Domains (IDs), Context Execution Modules (CEM), and Business System Read Contracts.

---

## 1. Executive Summary: The Diagnostic Finding

During an end-to-end trace to understand why semantically distinct queries (e.g., *"What are the BOM components for SKU 126BS?"* and *"What is the packing and shipment status for SKU 126BS?"*) both returned stock-balance responses, a systemic architectural flaw was uncovered.

### The Root Failure
1. **RABTA Cognitive Loop Succeeded:** Stages R-1 (Intent Extraction), R-2 (Requirement Classification), and R-3 (Abstract Evidence Request Formulation) successfully parsed natural language into structured semantic requirements (`desired_outcome = "BOM components"` or `"packing and shipment status"`).
2. **The Execution Bridge Failed:** The downstream adapter (`src/infrastructure/adapters/inventory_cem_adapter.py`) discarded the structured R-3 container and fell back to naive natural language substring matching on `query.lower()`:
   ```python
   # Legacy Brittle Bridge (inventory_cem_adapter.py):
   if "history" in query_lower or "ledger" in query_lower or "last week" in query_lower:
       target_urn = "urn:aarambooks:inventory:capability:ledger"
   elif "jobwork" in query_lower or "vendor" in query_lower or "pending with" in query_lower:
       target_urn = "urn:aarambooks:inventory:capability:jobwork_status"
   elif "exception" in query_lower or "mismatch" in query_lower:
       target_urn = "urn:aarambooks:inventory:capability:exception_status"
   else:
       # ⚠️ CRITICAL FLAW: Unmatched arbitrary read queries silently defaulted to stock balance!
       target_urn = "urn:aarambooks:inventory:capability:balance"
   ```
3. **The Root Architectural Cause:** The Context Execution Module (CEM)—originally conceived as a strict transactional contract layer—was forced to handle all simple read operations. Treating operational data lookups with the heavy boilerplate of distributed RPC microservices created so much engineering friction that developers implemented a temporary keyword bridge that broke the cognitive chain.

---

## 2. Canonical 4-Box Container Architecture (Zero Ambiguity)

To ensure every major organ sits in a distinct compartment without blurred boundaries or "spread legs," the ecosystem is strictly partitioned into **Four Autonomous Containers**:

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

> [!CAUTION]
> ### 🚨 CRITICAL AI AGENT INSTRUCTION: DO NOT BYPASS AZM 🚨
> When building or modifying any Intelligence Domain (ID), **you MUST NOT invent semantic or schematic knowledge inside the ID.** 
> **AZM (Aaram Zameer)** is the central, global repository for all semantic concepts (WHAT things mean) and schematic public read contracts (HOW things are queried). 
> Every agent working in this repository MUST integrate AZM as a separate layer and store all ontology and schema definitions in the `src/azm/` namespace. DO NOT mix Intelligence Domain logic with semantic knowledge. AZM has deep architectural and emotional meaning (resolve/determination) in this project and must remain the foundational source of truth for the AI's worldview.

### Strict Contract Rules Between Containers:


| Interaction | Who Talks to Whom | What is Exchanged (The Contract) |
| :--- | :--- | :--- |
| **Brain Core ➔ ID** | Orchestrator delegates to Domain | `process_query(user_utterance, session_history)` |
| **ID ➔ Azm** | ID queries domain definitions | `get_schema(namespace="inventory")` + `get_vocab()` |
| **ID ➔ Brain Core (Text-to-SQL)** | ID uses Brain Core's shared SQL service | `execute_sql(query, schema_from_azm) ➔ raw_data` |
| **Brain Core ➔ Business System** | SQL Runner queries the database | `SELECT ... FROM vw_* ➔ [raw_rows]` |
| **Business System ➔ Azm** | Business System publishes public views | Periodic sync of `vw_*` definitions into Azm |

---

## 3. End-to-End Read Substrate Lifecycle (Step-by-Step Flow)

The Intelligence Domain (ID) is the active domain specialist running throughout the entire lifecycle, leveraging Brain Core's shared platform services:

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

---

## 4. The Execution Split: Three Specialized Departments

Instead of forcing all interactions through a single monolithic CEM, the execution layer is partitioned by operational responsibility:

### 1. The Governed Read Substrate (The Filing Cabinet)
* **Intent:** `RETRIEVE` and `CALCULATE`.
* **Nature:** Fast, parameterized, operational reads (e.g. BOM components, stock balances, packing status, supplier lists).
* **Mechanism:** Dynamic, schema-grounded Text-to-SQL powered by local **Qwen 7B**, validated by a strict Python AST safety gate and executed on a read-only database connection.

### 2. The Strict CEM (The Vault)
* **Intent:** `ACTION` (Mutations / Writes).
* **Nature:** High-stakes transactional ledger operations (e.g. Stock adjustments, material issues, PO generation).
* **Mechanism:** Two-phase commit, cryptographic confirmation nonces (R-9), and strict domain service boundaries.

### 3. The Analytical Engine (The Data Scientist)
* **Intent:** Complex multi-dimensional aggregations and analytics.
* **Nature:** Long-range business intelligence (e.g. quarterly inventory turnover, stockout forecasting, holding cost trends).
* **Mechanism:** Read-replica / OLAP data warehouse queries preventing workload interference with the live operational database.

---

## 5. The Decoupling Paradox & Public Read Contracts

A central realization of this audit is resolving the dilemma between extreme decoupling and extreme rigidity:

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

### The Resolution: Stable Public Read Views (`vw_*`)
1. **Business Systems retain total autonomy:** The Inventory engineering team can refactor, partition, or normalize internal tables without breaking the AI.
2. **Stable Public Contract:** The Inventory system publishes clean, documented SQL views:
   * `vw_stock_balances` (`sku`, `item_name`, `on_hand`, `available`, `warehouse`)
   * `vw_bom_components` (`parent_sku`, `component_sku`, `quantity_required`, `uom`)
   * `vw_jobwork_status` (`vendor_name`, `sku`, `pending_quantity`, `issue_date`)
   * `vw_suppliers` (`supplier_name`, `gst_number`, `item_sku`)
3. **Azm Ingestion:** Azm periodically ingests these view definitions into its `inventory` namespace.
4. **Qwen Generation:** When an inventory read query arrives, Qwen receives the verified view schema from Azm and dynamically generates the exact, optimal `SELECT` statement.

---

## 6. Azm: From In-Memory Prototype to AI Training Flywheel

### Current State vs. Target State
* **Current State (`InMemoryAzmProvider`):** Static Python list in RAM holding concepts, aliases, and policy boundaries for the `inventory` namespace.
* **Target State (Database Federation):** 
  1. `azm_concepts`: Dynamic concept graph supporting Admin UI management for aliases and terminology across all domains (`inventory`, `ndr`, `customer`).
  2. `azm_trajectories`: Ground-truth dataset recording (*User Query* → *Semantic Resolution* → *Executed Query* → *Feedback*).

### The Long-Term Vision (ADR-009 Grounding):
Azm is the proprietary data asset of AaramBooks. The accumulated trajectories will be used to **fine-tune local open-weight models (Qwen)** so they natively understand Aaram business logic, eliminating reliance on frontier models and massive prompt engineering.

---

## 7. Dynamic Text-to-SQL Grounded Execution Flow

```
   [ User's Natural Query ]
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  Azm Context Injection (The Aaram Grounding Lens)          │
│  - "Karigar / Tailor" ➔ maps to `jobwork_vendor`            │
│  - "Available stock"  ➔ `on_hand_quantity - allocated_qty`  │
│  - "BOM Components"   ➔ `vw_bom_components` view            │
│  - Table Schemas + Relations                                │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Qwen 7B (Text-to-SQL Engine)                               │
│  Now Qwen knows BOTH:                                       │
│  1. Perfect SQL syntax (from pre-training)                  │
│  2. Exact Aaram business meaning (from Azm)                 │
│  ➔ Generates precise, un-hallucinated SQL                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Read-Only Safety Gate (Python)                             │
│  - AST Parse: Enforces `SELECT` only                        │
│  - Executes on PostgreSQL Read-Only Connection              │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Why This Container Architecture Scales With Zero Code Duplication

1. **Adding a New Domain (e.g. NDR / Logistics) takes 1 Day:**
   * No new orchestrator, Text-to-SQL engine, memory, or safety gates need to be written.
   * Add `ndr.*` terms and view schemas into **Azm**, add a lean `src/intelligence_domains/ndr/` reasoning folder, and the new domain is live.
2. **Backend Engineering Independence:**
   * The backend team can refactor internal tables anytime without breaking the AI as long as public `vw_*` views are maintained.
3. **Seamless Model Upgrades:**
   * Switching to a fine-tuned local Qwen model requires changing 1 configuration line in Brain Core's Model Gateway; all domains immediately benefit.

---

## 9. Immediate Realignment Plan

1. **Deprecate the Legacy Keyword Router:**
   * Remove the `else: target_urn = "...balance"` fallback in `src/infrastructure/adapters/inventory_cem_adapter.py`.
2. **Build the Text-to-SQL Read Substrate Service in Brain Core:**
   * Implement `src/brain_core/sql/engine.py` (or adapter) with AST `SELECT`-only validation and read-only DB execution.
3. **Register the Public Read Views in Azm:**
   * Add public view definitions for BOM, Packing, Suppliers, and Jobwork to Azm's `inventory` namespace.
4. **Wire Dynamic Dispatch in Inventory ID:**
   * Allow `InventoryIntelligenceOrchestrator` to route read requests dynamically to the Read Substrate.
5. **Unlock Pending Capabilities:**
   * Verify end-to-end execution for BOM queries, packing slip lookups, supplier searches, and stock balances without hardcoded keyword bridges.
