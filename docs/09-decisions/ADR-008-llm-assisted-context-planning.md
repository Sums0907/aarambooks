# ADR-008: LLM-Assisted Context Planning

## Status
Accepted

## Decision
Brain Core will introduce an **LLM-Assisted Cognitive Context Planning** layer to sit conceptually above the deterministic Context Engine. 

When Brain receives an arbitrary natural-language query, it will not map it deterministically to predefined Context Capabilities. Instead, a Cognitive Planner (LLM) will:
1. Decompose the NL question.
2. Interrogate Brain Core for business semantics and schemas (Dynamic Discovery).
3. Generate a dynamic Retrieval Plan.
4. Pass the plan to the Context Engine for deterministic, governed, read-only execution.
5. Iteratively request more evidence if the initial results are insufficient.
6. Package the final provenance-tagged evidence and hand it to a Reasoning LLM to synthesize the final answer.

## Architectural Intent
This decision ensures Brain Core is genuinely capable of answering arbitrary, unseen business questions across the ecosystem, moving beyond a brittle, deterministic query-matching system. 

It explicitly establishes a **Hybrid Context Model**:
- Brain will leverage highly optimized **Predefined Context Capabilities** when they match the Planner's needs.
- Brain will fall back to **Dynamic Data Discovery** (via governed read-models or semantic APIs) when the question requires ad-hoc data analysis.

## Security & Governance Rules
This decision explicitly **DOES NOT** grant the LLM direct SQL access to production databases.
- The LLM Planner only *proposes* evidence requirements.
- The deterministic Context Engine *executes* them.
- All dynamic queries must pass through a strict semantic layer or read-only API that enforces authorization, timeouts, tenant isolation, and prevents destructive operations (No `DROP`, `UPDATE`, `INSERT`).

## Consequences
- Requires designing a robust `EvidencePackage` contract.
- Requires building semantic metadata repositories so the LLM can understand business terms (e.g., "leakage", "yield") and workflows (e.g., Order -> Pick -> Ship) before querying.
- Requires iterative context merging capabilities in the Context Engine.
- Requires explicit abstraction of the LLM Provider (e.g., Gemini) to prevent vendor lock-in at the core orchestration level.
