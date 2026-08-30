# Architecture Impact Report: LLM-Assisted Context Planning

## 1. Primary Architectural Decision
Aaram Brain explicitly supports **arbitrary natural-language business questions without requiring a predefined Context Capability for every possible question.**

Predefined Context Capabilities remain valid and valuable, but they are **reusable, governed retrieval abstractions/accelerators**, NOT the exhaustive universe of information Brain can retrieve or reason about.

The architecture supports both mechanisms coexisting:
```text
[KNOWN REQUIREMENT]
        ↓
Existing Context Capability
        ↓
Deterministic Provider
        ↓
Evidence

[UNKNOWN / NOVEL REQUIREMENT]
        ↓
Cognitive Planner
        ↓
Evidence Plan
        ↓
Dynamic Discovery
        ↓
Governed Retrieval
        ↓
Evidence
```

## 2. The Boundary: Cognitive Planner vs Orchestrator vs Context Engine
The architecture strictly separates intent from execution:
- **Cognitive Planner:** "What do I need to know?" (Interprets NL, determines required evidence, proposes Evidence Plan).
- **Brain Orchestrator:** "Is this request valid and how should it be executed?" (Validates plan, resolves mechanisms, enforces authorization).
- **Context / Evidence Engine:** "Retrieve, normalize, combine and prove the evidence." (Executes retrieval, handles provenance).
- **Business Systems:** "Own the operational truth." (Provides data).

## 3. Evidence Plan (First-Class Concept)
The **Evidence Plan** is a machine-readable representation of *what evidence Brain believes it needs* to answer the user's question, structurally distinct from *how* the evidence is retrieved.
It may contain:
- Original question and interpreted objective.
- Required facts, relationships, metrics, and comparisons.
- Required workflow/state information.
- Filters and time ranges.
- Preferred existing Context Capabilities or dynamically discovered evidence requirements.
- Uncertainties, ambiguities, or dependencies for multi-stage retrieval.

**CRITICAL RULE:** The Evidence Plan does NOT mean LLM-generated SQL against a production database. The LLM only plans; the deterministic infrastructure governs and retrieves.

## 4. Semantic Knowledge Requirement
Database schemas are insufficient for dynamic discovery. Brain requires governed **Brain Knowledge**, distinct from Context Capabilities. Brain Knowledge describes:
- **Data structure:** Databases, tables, foreign keys.
- **Business semantics:** e.g., meaning of leakage, variance, jobwork issue, material receipt.
- **Workflow semantics:** e.g., Order -> Pick -> Pack -> Shipment.
- **State semantics:** Order states, Inventory states, etc.
- **Derived metrics:** Valuation, efficiency, COGS.

## 5. Reworked Jobwork Example
Query: *"Which jobwork vendor has the highest unexplained material leakage this month?"*

**Path A — Existing capability (Accelerator)**
```text
Question
 ↓
Cognitive Planner
 ↓
Evidence Plan
 ↓
JOBWORK_CONTEXT + INVENTORY_MOVEMENTS
 ↓
Context Engine
 ↓
Evidence
 ↓
Reasoning
```

**Path B — Dynamic discovery**
```text
Question
 ↓
Cognitive Planner
 ↓
Evidence Plan
 ↓
No exact capability
 ↓
Discover: jobwork entities, material issue/receipt, scrap, reconciliation
 ↓
Governed retrieval
 ↓
Evidence
 ↓
Reasoning
```
Both paths are valid and handled dynamically by the Orchestrator.

## 6. The 17 Sample Queries
The 17 historical queries are strictly **validation scenarios**, not architectural constraints. They must NOT be used to enumerate the complete set of Context Capabilities Brain is allowed to use.

## 7. Model Provider Independence
**Gemini is an LLM provider, not a Brain architectural dependency.** 
The Model Gateway remains provider-independent, supporting Gemini alongside potential future open-source models (e.g., Llama/Qwen) for bounded workloads, while maintaining the same architectural abstraction.
