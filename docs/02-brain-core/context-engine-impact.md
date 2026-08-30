# Context Engine Impact: Cognitive Planning Enhancements

The introduction of LLM-Assisted Context Planning fundamentally shifts the Context Engine from a simple mapping registry to a deterministic orchestration substrate capable of dynamic retrieval.

## 1. Deterministic vs Dynamic Retrieval
The Context Engine must support:
- **A. Predefined Capabilities:** Direct resolution to known providers (e.g., `ORDER_STATE`).
- **B. Dynamic Evidence Retrieval:** Using an `Evidence Plan` to execute governed, semantic queries when no exact predefined capability exists.
- **C. Composite Evidence:** Assembling evidence from both predefined capabilities and dynamic semantic queries simultaneously.
- **D. Iterative Expansion:** Adding additional evidence after an initial retrieval, based on iterative loops from the Cognitive Planner.

## 2. Provenance Guarantees
Every factual component in the Evidence Package must retain:
- Source (Which system provided it).
- Retrieval timestamp.
- Relevant business timestamp/period.
- Transformation/derivation metadata where applicable (distinguishing raw facts from derived facts).

## 3. Revised Error Model
The generic `ProviderNotRegisteredError` is insufficient. The engine must conceptually distinguish failures, such as:
- `DATA_UNAVAILABLE` (Underlying truth does not exist).
- `DATA_INACCESSIBLE` (Truth exists, but Brain cannot retrieve it).
- `CAPABILITY_NOT_REGISTERED` (No reusable predefined capability exists, though dynamic retrieval might still work).
- `SEMANTIC_KNOWLEDGE_MISSING` (Brain lacks understanding of the business meaning).
- `SCHEMA_KNOWLEDGE_MISSING` (Schema definitions are unknown).
- `EVIDENCE_INSUFFICIENT` (Retrieval succeeded, but didn't yield enough data).
- `EVIDENCE_CONFLICT` (Multiple sources contradict).
- `QUERY_NOT_PERMITTED` (Authorization/governance blocked it).
- `RESOURCE_LIMIT` (Query too large).
- `SOURCE_FAILURE` (Business system down).
- `PLANNING_AMBIGUITY` (LLM couldn't formulate a plan).

## 4. The "Context Gap" Distinction
A missing Context Capability is no longer automatically a hard limit. 
*Underlying truth unavailable ≠ Brain cannot retrieve it ≠ No reusable capability exists.*
If no predefined capability exists, the Brain Orchestrator may simply fall back to Dynamic Retrieval. True gaps only occur when the underlying data is inaccessible or Brain lacks the semantic knowledge to query it.
