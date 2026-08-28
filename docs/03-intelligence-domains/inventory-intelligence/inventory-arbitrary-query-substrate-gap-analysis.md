# Inventory Intelligence: Arbitrary Query Substrate Gap Analysis

## 1. Executive Summary

This document establishes the architectural gap analysis for enabling the AaramBooks Inventory Intelligence domain to process arbitrary, previously unseen natural-language inventory questions. It defines the strict separation of ownership between Brain Core (infrastructure), AaramInventory (business truth), Inventory Intelligence (domain reasoning), and Azm (the evolving proprietary intelligence asset). 

This analysis confirms that the Phase 14 implementation of Brain Core provides a generic orchestration skeleton but requires a robust Semantic Infrastructure to translate semantic intent into physical capability execution.

### Formal Distinctions

**1. Semantic Infrastructure vs Semantic Knowledge**
- **SEMANTIC INFRASTRUCTURE (Brain Core):** Generic machinery for processing, resolving, discovering, translating, and using semantic information. Brain Core provides the machinery. It resolves domain-provided semantic requirements into concepts, entities, relationships, states, attributes, parameters, and forms that can be matched against capabilities.
- **SEMANTIC KNOWLEDGE (Intelligence Domain / Azm):** Domain-specific knowledge defining what business terms, entities, relationships, states, workflows and concepts mean (e.g., "low stock means X"). The domain provides the meaning.

**2. Context Infrastructure vs Context Capability**
- **CONTEXT INFRASTRUCTURE (Brain Core):** Generic machinery for planning, resolving, authorizing, retrieving, normalizing, combining and tracking evidence. It determines HOW evidence is obtained and governed.
- **CONTEXT CAPABILITY (Business System):** An authoritative business-system capability through which operational truth can be obtained (regardless of transport: REST, read model, etc.). It represents WHAT authoritative business truth a system can provide.

**3. Cognitive Infrastructure (Brain Core)**
- Generic machinery such as Cognitive Planner, Brain Orchestrator, LLM Gateway, and bounded planning loops.

**4. Intelligence Domain**
- Independent domain (e.g., Inventory Intelligence) that owns domain semantics, reasoning, calculations, interpretation, and synthesis. It consumes Brain Core services and must NOT own operational truth.

### Key Architectural Invariant

- **Semantic Infrastructure** answers HOW meaning is resolved.
- **Semantic Knowledge** answers WHAT that meaning is in the Aaram ecosystem.

- **Context Infrastructure** answers HOW evidence is obtained and governed.
- **Context Capability** represents WHAT authoritative business truth a business system can provide.

Business Systems own truth.
Brain Core owns generic cognitive, semantic and context machinery.
Intelligence Domains own domain meaning and reasoning.
Azm accumulates Aaram's proprietary intelligence knowledge and experience across domains.

---

### Canonical Ownership Model

| WHAT IT IS | OWNER |
| :--- | :--- |
| **Semantic Infrastructure** (Machinery for resolving meaning) | **Brain Core** |
| **Semantic Knowledge** (Aaram/domain meaning) | **Intelligence Domain / Azm** |
| **Context Infrastructure** (Machinery for obtaining/governing evidence) | **Brain Core** |
| **Context Capability** (Authoritative business-system ability to provide truth) | **Business System** |
| **Cognitive Infrastructure** (Machinery for orchestration/control) | **Brain Core** |
| **Operational Truth** (Business data and state) | **Business System** |
| **Domain Reasoning** (Calculations, synthesis, evaluation) | **Intelligence Domain** |
| **Azm** (Ecosystem-wide evolving proprietary intelligence asset) | **AaramBooks** |

---

## 2. Requirements for an Arbitrary Inventory Question

### A. What does an arbitrary inventory question require?
An arbitrary inventory question (e.g., "Which SKUs are low in stock and need urgent replenishment?") requires the system to dynamically interpret user intent, deduce the required factual evidence without hardcoded mappings, obtain that evidence from business systems securely, and apply domain-specific logic to synthesize a governed answer.

### B. What semantic work is required?
The system must translate ambiguous human vocabulary ("low stock", "replenishment", "jobwork issue", "leakage") into standardized business concepts, entities, relationships, and state definitions before data can be retrieved.

### C. What cognitive work is required?
The system must formulate an `EvidencePlan`, evaluate the sufficiency of returned evidence, decompose complex multi-stage intents, and govern the safety and deterministic bounds of LLM reasoning.

### D. What evidence work is required?
The system must resolve abstract semantic concepts into physical retrieval mechanisms, execute the retrieval against authoritative sources, normalize the resulting data, maintain strict provenance for every fact, and assemble an `EvidencePackage`.

### E. What must Brain Core provide as generic infrastructure?
Brain Core must provide the machinery: Semantic Infrastructure (how meaning is processed), Context Infrastructure (how evidence is obtained and governed), and Cognitive Infrastructure (how planning, validation, and model execution are orchestrated).

### F. What must Inventory Intelligence provide as domain knowledge/reasoning?
The domain must provide Semantic Knowledge (what inventory terms mean), Domain Knowledge (inventory business rules, thresholds like "low stock", derived calculations like COGS), and the synthesis of the final intelligence answer.

### G. What must AaramInventory provide as context capabilities?
AaramInventory must provide the operational truth via Context Capabilities—governed mechanisms to read physical state (e.g., SKU catalog, inventory balances, ledger movements) regardless of the transport protocol.

### H. What belongs to Azm?
Azm (عزم) is Aaram's long-term proprietary intelligence asset across the entire Aaram ecosystem. It is **NOT** synonymous with Inventory Intelligence. It accumulates Semantic Knowledge, Cognitive/Domain knowledge, reasoning patterns, evidence-plan patterns, historical evaluation data, human feedback, and model-specialization datasets.

### I. What already exists?
- **Cognitive Infrastructure:** `CognitivePlanner`, `BrainOrchestrator`, LLM Gateway abstraction.
- **Context Infrastructure:** `CapabilityResolver`, `ContextAssembler`, `ProviderRegistry`, `EvidencePlan` contracts.
- **Context Capabilities:** Basic AaramInventory SKU and balance lookup (via REST API).

### J. What is merely a stub/proof?
- `ContextAssembler.assemble_evidence()` is currently a Phase 14 mock that returns static data for exact capability matches.
- The `EvidenceRequirement` entity lacks physical resolution fields beyond natural language semantic descriptions.

### K. What is genuinely missing?
- **Semantic Infrastructure:** A mechanism inside Brain Core to lookup and translate semantic descriptions into physical entity references (e.g., SKU UUIDs) and business-system parameters.
- **Dynamic Evidence Assembly:** Physical adapter execution within the dynamic orchestration boundary.
- **Context Capabilities:** Ledger history, jobwork details, and anomaly tracking capabilities in AaramInventory.

### L. What is incorrectly placed today?
No major structural violations currently exist. The Phase 14 implementation successfully resisted domain leakage. However, attempting to integrate an arbitrary query boundary directly into the `event_bus` webhook infrastructure would incorrectly conflate system webhooks with domain APIs.

### M. What should NOT be built?
- Inventory logic inside Brain Core.
- Hardcoded APIs or prompt branches for specific questions.
- Unrestricted LLM database access/SQL generation.
- A bypass of the Brain Core Context Engine.

### N. What must be built before the first real arbitrary-query proof?
- A Semantic Infrastructure layer in Brain Core capable of mapping semantic requirements to capability parameters.
- The physical execution link in `ContextAssembler.assemble_evidence()`.
- The isolated Inventory Intelligence Domain application boundary.

---

## 3. Explicit Lifecycle Gap Matrix

| Stage | Owner | Infrastructure vs Knowledge | Current Status | Required Change |
| :--- | :--- | :--- | :--- | :--- |
| **1. User Query** | Domain | Interface | Missing | Create isolated domain entry point |
| **2. Domain Identification** | Brain Core / Domain | Infrastructure | Stubbed | Explicit routing mechanism needed |
| **3. Semantic Interpretation** | Domain | Knowledge (Azm) | Missing | LLM prompt/knowledge integration |
| **4. Semantic Knowledge Retrieval** | Brain Core | Infrastructure | Missing | Build dynamic Semantic Discovery layer |
| **5. Cognitive Planning** | Brain Core | Infrastructure | Implemented | None (Phase 14 complete) |
| **6. Evidence Plan** | Brain Core | Infrastructure | Implemented | None (Phase 14 complete) |
| **7. Evidence Requirement Resolution** | Brain Core | Infrastructure | Stubbed (Semantic Only) | Expand to include physical parameters |
| **8. Entity / Parameter Resolution** | Brain Core | Infrastructure | Missing | Build translation from semantics to physical IDs |
| **9. Capability Discovery** | Brain Core | Infrastructure | Basic | Expand `ProviderRegistry` for dynamic lookup |
| **10. Capability Resolution** | Brain Core | Infrastructure | Implemented | None |
| **11. Authorization** | Brain Core | Infrastructure | Implemented | Enforce M2M across dynamic bounds |
| **12. Physical Retrieval** | Brain Core | Infrastructure | Mocked in Phase 14 | Connect physical adapters in `assemble_evidence` |
| **13. Context Normalization** | Brain Core | Infrastructure | Basic | Standardize payload structures |
| **14. Evidence Combination** | Brain Core | Infrastructure | Basic | Support multi-source assembly |
| **15. Provenance** | Brain Core | Infrastructure | Basic | Ensure strict tracking per fact |
| **16. Evidence Sufficiency** | Brain Core | Infrastructure | Implemented | None |
| **17. Evidence Extension / Iteration**| Brain Core | Infrastructure | Implemented (Bounded) | None |
| **18. Domain Reasoning** | Domain | Logic | Missing | Implement domain-specific evaluation |
| **19. Deterministic Calculation** | Domain | Logic | Missing | Implement math/threshold bounds outside LLM |
| **20. Insight Synthesis** | Domain | Logic | Missing | LLM integration for response generation |
| **21. Answer Generation** | Domain | Logic | Missing | Return structured intelligence |
| **22. Evaluation** | Domain | Knowledge (Azm) | Missing | Establish automated test harness |
| **23. Feedback / Learning** | Domain | Knowledge (Azm) | Missing | Capture user correction telemetry |
| **24. Azm accumulation** | Azm | Asset | Missing | Establish storage patterns for reasoning |

---

## 4. Phase 14 Gap Investigation

1. **`ContextAssembler.assemble_evidence()`**: This is currently a **stub/proof**. It accurately models the Gap Semantics but returns a hard-coded payload `{"mock_data": ...}`. It must be updated to invoke physical adapters.
2. **`EvidenceRequirement`**: Currently insufficient for physical retrieval. It contains only `semantic_description`. It needs a bridge to map semantics to `item_references` (e.g. SKU strings/UUIDs) expected by `AaramInventoryAdapter`.
3. **Semantic Knowledge → Context Capability**: Domain knowledge must describe meaning (e.g., "Jobwork means material sent to vendor") which Brain Core Semantic Infrastructure uses to discover the corresponding Context Capability without the Domain knowing the DB tables.
4. **Context Capability → Retrieval**: Brain Core resolves abstract capabilities to physical retrieval via the `ProviderRegistry`, which delegates to interface-compliant Python adapters (hiding the REST/DB transport).
5. **Multiple Evidence Requirements**: Supported architecturally by `EvidencePlan` taking a list of requirements, but requires the physical assembly layer to execute concurrently.
6. **Evidence Sufficiency / Extension**: Implemented and bounded (max 3 iterations) by `BrainOrchestrator`.
7. **Provenance**: Structurally modeled in `EvidenceItem`, but relies on adapters correctly injecting timestamps and source identifiers.
8. **Dynamic Discovery**: Currently a conceptual fallback yielding `CONTEXT_CAPABILITY_UNAVAILABLE`. True dynamic discovery requires the missing Semantic Infrastructure.

---

## 5. Architectural Non-Goals

1. **Not API-Centric**: Intelligence Domains request evidence via Semantic Requirements, not by picking API endpoints.
2. **Not Database-Centric**: LLMs will never generate SQL against operational databases. Schema metadata informs governed capabilities, but does not bypass authorization.
3. **No Inventory Logic in Brain Core**: Brain Core will not contain inventory-specific planners, adapters, or rules.

---

## 6. Dependency-Ordered Implementation Roadmap

**Stage A — Generic Semantic Resolution Infrastructure**
- **Objective:** Build the generic Brain Core machinery required to resolve domain-provided semantic requirements into concepts, entities, relationships, states, attributes, parameters and Context Capability-compatible requirements. Stage A must NOT implement inventory business semantics, nor attempt to answer the 17 inventory evaluation scenarios individually.
- **Owner:** Brain Core
- **Unlocks:** Dynamic capability execution.

**Stage B — Physical Evidence Assembly**
- **Objective:** Replace the mock in `ContextAssembler.assemble_evidence()` with actual `ProviderRegistry` adapter execution.
- **Owner:** Brain Core
- **Unlocks:** Real data retrieval for arbitrary queries.

**Stage C — Inventory Intelligence Domain Shell**
- **Objective:** Create the isolated Python application boundary for `inventory_intelligence` that invokes `BrainOrchestrator`.
- **Owner:** Intelligence Domain
- **Unlocks:** Safe routing of natural-language questions.

**Stage D — Inventory Domain Knowledge & Azm Integration**
- **Objective:** Establish the Inventory domain's Semantic Knowledge and domain reasoning knowledge, and how it contributes to the broader Azm asset. Establish evaluation/experience capture required for future learning.
- **Owner:** Inventory Intelligence / Azm boundary
- **Unlocks:** Domain-specific deterministic reasoning and future model training.

**Stage E — Arbitrary-Query Proof Validation**
- **Objective:** Execute the first genuine arbitrary-query proof against the full pipeline.
- **Owner:** Inventory Intelligence + Brain Core
- **Unlocks:** Confidence in the cognitive orchestration architecture.

**Stage F — Context Capability Expansion**
- **Objective:** Build new AaramInventory capabilities (ledger, jobwork) to support advanced queries.
- **Owner:** Business System (AaramInventory)
- **Unlocks:** Advanced intelligence scenarios.

---

## 7. Arbitrary-Query Architecture Flow

The complete architectural flow from user intent to Azm accumulation is:

```text
USER QUERY
  ↓
Intelligence Domain
  ↓
Cognitive Infrastructure
  ↓
Cognitive Planner
  ↓
Evidence Plan
  ↓
Semantic Resolution Infrastructure
  ↓
Domain Semantic Knowledge
  ↓
Concept / Entity / State / Parameter Resolution
  ↓
Context Capability Resolution
  ↓
Context Infrastructure
  ↓
Business System Context Capability
  ↓
Authoritative Business Truth
  ↓
Evidence Package
  ↓
Domain Reasoning
  ↓
ANSWER
```

---

## 8. First Genuine Arbitrary-Query Proof

The first proof is **NOT** answering a single hard-coded "low stock" question. 

The proof is: **"Demonstrate that the Inventory Intelligence domain can accept multiple previously unseen natural-language inventory questions and independently determine and obtain the evidence required to answer them."**

The architecture must successfully process questions requiring:
- Direct lookup (Current balance)
- Aggregation (Total stock across locations)
- Filtering/Thresholds (Low stock)
without adding question-specific orchestration code.

---

## 8. Azm (عزم) Formal Architectural Position

Azm is Aaram's long-term proprietary intelligence asset. It is NOT Brain Core, NOT a single Intelligence Domain, NOT an Inventory database, NOT merely a dictionary or prompt library. It is the evolving body of Aaram-specific intelligence knowledge and experience that can ultimately be used to train/specialize future open-weight models.

Azm accumulates knowledge across all Aaram domains:

```text
                         AZM
             Aaram proprietary intelligence asset
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
   Semantic Knowledge   Cognitive/Domain   Experience &
                       Knowledge           Learning Data
          │                 │                 │
          └──────────────┬──┴─────────────────┘
                         │
          ┌──────────────┼───────────────┐
          │              │               │
      Inventory         NDR        Customer Query
      contribution   contribution   contribution
          │              │               │
          └──────────────┴───────────────┘
                         │
                  Future Aaram Model
```

The current architecture ensures Azm readiness by enforcing ownership boundaries:
- **Runtime Infrastructure** (Brain Core) remains distinct from knowledge.
- **Semantic/Domain Knowledge** (What "low stock" means) is isolated, making it portable as fine-tuning data for future open-weight models (e.g., Qwen).
- **Reasoning Patterns** (The `EvidencePlan` schemas) accumulate as a training dataset of "how to solve business problems".
- **Evidence Packages** provide perfectly structured input/output pairs for evaluating model performance independently of live systems.

---

## 10. Future Open-Weight Model Strategy

This separation is intentional for Aaram's long-term model strategy.

Aaram should own:
- Semantic Knowledge
- Domain Knowledge
- Context/evidence patterns
- Reasoning patterns
- Evaluation scenarios
- Historical examples
- Human feedback
- Successful/failed reasoning traces

These progressively become proprietary Azm assets and future training/specialization material. The LLM remains replaceable. No particular model (Qwen, Gemini, Claude, OpenAI) is part of the architecture.

The architecture supports the long-term Aaram intelligence strategy:
`capable open-weight model + Aaram/Azm proprietary knowledge + Brain Core orchestration + governed context + domain reasoning`
