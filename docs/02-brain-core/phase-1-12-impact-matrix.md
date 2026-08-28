# Phase 1–12 Architecture Impact Matrix

This matrix assesses the impact of the **LLM-Assisted Context Planning** reassessment on the architectural decisions established in Phases 1–12.

| Architectural Area / Assumption | Current Assessment | Classification | Required Change & Reason | Implementation Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Brain / Business System Separation** | Business systems own truth. Brain Core owns intelligence. | **KEEP** | None. Brain must still retrieve truth via governed adapters, not duplicate it. | None |
| **Context Engine & Assembler** | Assembles context deterministically using predefined capabilities. | **KEEP WITH EXTENSION** | Must be extended to support iterative, dynamic evidence retrieval and context merging. | High (Needs iteration & dynamic resolution support) |
| **Context Capabilities Model** | Capabilities represent the *complete universe* of obtainable truth. | **MODIFY** | Capabilities remain as optimized shortcuts, but are supplemented by dynamic discovery for arbitrary queries. | Medium |
| **Context Gaps (ProviderNotRegistered)** | Treat all missing pre-defined capabilities as hard failures. | **MODIFY** | Brain must distinguish between "Capability not registered" and "Data does not exist / Semantic Gap". | Medium |
| **LLM Execution Timing** | LLM executes only at the end to reason over facts. | **SUPERSEDE** | LLM must also be used upfront as a Cognitive Planner to decompose NL and plan retrieval. | High (New planning step) |
| **AI Model Gateway** | Abstracts prompts from specific LLMs. | **KEEP WITH EXTENSION** | Must cleanly abstract the "Cognitive Planner" role from the "Reasoning" role, supporting iterative model calls. | Low (Gateway concept holds) |
| **Data Models (Schemas)** | Rigid Pydantic schemas for standard contexts. | **KEEP WITH EXTENSION** | Must also support a generic `EvidencePackage` wrapper for dynamically discovered, heterogeneous facts. | Medium |
| **Security & Physical Auth** | M2M RS256 token validation for internal APIs. | **KEEP** | Governed read-only execution heavily relies on these established identities. | None |
| **Identity Contract (aaram_brain)** | Specific 5 permissions without arbitrary `brain:invoke`. | **KEEP** | The LLM Planner operates *within* these strict permissions when generating retrieval plans. | None |
| **Provenance Tracking** | Tagging `SourceSystem` and `retrieval_timestamp`. | **KEEP WITH EXTENSION** | Crucial for the LLM to differentiate raw truth from derived truth. Must persist across iterative fetches. | Low |
| **17 Inventory Questions as Boundary** | The 17 sample queries define the required capability scope. | **SUPERSEDE** | The 17 queries are merely examples. Brain must handle arbitrary questions. | None (Mindset change) |
