# Context Engine Impact: Cognitive Planning Enhancements

The introduction of LLM-Assisted Context Planning requires the following conceptual enhancements to the Brain Core Context Engine. These changes elevate the Context Engine from a static fetcher to a dynamic orchestration substrate.

## 1. ContextAssembler
- **Iterative Context Expansion:** The `ContextAssembler` must support sequential calls for the same session. If the LLM Planner requests `evidence_B` after analysing `evidence_A`, the Assembler must merge `B` into the ongoing context state without overwriting `A`.
- **Dynamic Query Execution:** The Assembler must be capable of routing dynamic read-only queries (e.g., Semantic SQL, GraphQL) to the appropriate `SourceSystem` when a predefined capability is not used.
- **Evidence Sufficiency Checking:** The Assembler must track what was asked for vs. what was retrieved, allowing the LLM to know if a fetch yielded zero results.

## 2. ContextAssemblyRequest
- Must support **Iterative Identifiers:** E.g., `parent_request_id` or `session_id` to link multi-turn fetches.
- Must support **Dynamic Queries:** In addition to requesting `[ProviderCapability.CUSTOMER]`, it must be able to carry a `DynamicRetrievalPlan` (e.g., a governed semantic query payload).

## 3. ProviderRegistry & SourceSystem
- **Semantic Discovery Providers:** The Registry must include providers capable of returning *metadata and schemas*, not just raw data. The LLM Planner will query the registry for "What is the schema for Inventory Movements?" before querying the data itself.

## 4. Error Model (Granular Gaps)
The generic `ProviderNotRegisteredError` is no longer sufficient. The Context Engine must formally distinguish between:
- **Data Availability Gap:** "The database executed the query, but no records exist."
- **Data-Access Gap:** "The data exists, but the physical adapter/endpoint to reach it is not yet built or authorized."
- **Semantic/Knowledge Gap:** "I can access the table, but I lack the semantic metadata to understand what 'column_x' means."

## 5. Evidence Representation & Provenance
The returned context cannot just be a flat JSON dictionary. It must be a structured **Evidence Package** that clearly delineates:
- **Raw Fact:** Direct from the database.
- **Metadata:** `SourceSystem`, `retrieval_timestamp`.
- **Query Provenance:** The exact parameters/query used to fetch this specific fact, so the LLM knows *how* the data was sliced (e.g., "Filtered by last 30 days").
- **Conflicts:** If dynamic retrieval contradicts a predefined capability, both are preserved side-by-side with their distinct provenances for the Reasoning LLM to evaluate.
