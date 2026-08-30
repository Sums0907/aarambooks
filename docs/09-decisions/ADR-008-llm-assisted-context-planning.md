# ADR-008: LLM-Assisted Context Planning

## Status
Accepted

## Decision
Brain Core will introduce an **LLM-Assisted Cognitive Context Planning** layer, a formal **Evidence Plan**, and a **Brain Orchestrator** to handle arbitrary natural-language business questions without requiring predefined Context Capabilities for every possible query.

When Brain receives an arbitrary natural-language query:
1. **Cognitive Planner (LLM)** interprets the user's intent, decomposes the question, and proposes a machine-readable **Evidence Plan** outlining what facts, schemas, relationships, or filters are required.
2. **Brain Orchestrator** validates the Evidence Plan, enforces authorization, and sequences the retrieval.
3. **Context Engine** retrieves the evidence using either highly-optimized **Predefined Context Capabilities** (when they exist and match) OR **Dynamic Discovery** (governed, read-only retrieval using Brain Knowledge like schemas and semantics).
4. **Context Engine** returns a provenance-tagged **Evidence Package**.
5. This process can be **iterative**: the Cognitive Planner may evaluate the initial Evidence Package and request further evidence.
6. A **Reasoning LLM** synthesizes the final answer or recommendation.

## Architectural Intent
This decision establishes that Predefined Context Capabilities are reusable accelerators, not exhaustive limits. The architecture supports arbitrary NL by enabling the LLM to dynamically propose evidence needs. 

Crucially, it establishes explicit boundaries:
- **Cognitive Planner:** Owns "What do I need to know?"
- **Brain Orchestrator:** Owns "Is this request valid and how should it be executed?"
- **Context/Evidence Engine:** Owns "Retrieve, normalize, combine and prove the evidence."
- **Business Systems:** Own the operational truth.

It also distinguishes **Brain Knowledge** (governed understanding of data schemas, business semantics, workflows, and derived metrics needed for dynamic discovery) from **Context Capabilities** (reusable fetch logic for common truths).

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
