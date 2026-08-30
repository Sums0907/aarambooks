# General NL / LLM-Assisted Context Planning Review Output

**1. What was correct.**
- The deterministic `Context Engine` foundation (`ContextAssembler`, `ProviderRegistry`, `SourceSystem` abstraction).
- The principle that business systems own truth, and Brain orchestrates context retrieval through governed boundaries.
- Provenance tracking (timestamp, source system).
- The separation between Brain Core generic capabilities and domain-specific intelligence (e.g., `inventory-intelligence`).

**2. What was incomplete.**
- The concept of context building was strictly single-pass.
- The `ContextAssembler` lacked the capability to iteratively expand an `EvidencePackage` during multi-turn LLM evidence gathering.
- The distinction between a missing physical capability vs. missing data vs. missing semantic meaning was collapsed into a generic `ProviderNotRegisteredError`.

**3. What was architecturally restrictive.**
- The assumption that an intent must map 1:1 to a predefined `Context Capability` (like `JOBWORK_CONTEXT`). This prevented Brain from dynamically answering arbitrary queries that fall outside hardcoded capability mappings.
- The belief that the 17 inventory sample queries represented the bounds of the system rather than mere validation scenarios.

**4. What must change.**
- **Cognitive Context Planner:** We must insert an LLM-assisted cognitive planning layer before the deterministic Context Engine. This layer parses arbitrary NL, requests schema/semantic knowledge, and formulates a dynamic `Retrieval Plan`.
- **Dynamic Context Discovery:** The Context Engine must support executing governed semantic/read-only queries, not just statically coded capabilities.
- **Hybrid Context Model:** Brain must support *both* predefined capabilities (for common paths) and dynamic retrieval (for arbitrary exploration).
- **Phase Sequence:** Phase 13 (Adapter Implementation) must be postponed. We need a new architecture/documentation phase to flesh out the Semantic Discovery interface and Iterative Context Assembler logic.

**5. What does NOT need to change.**
- **No LLM to Raw DB:** The LLM still does NOT execute arbitrary SQL against production databases. The deterministic Context Engine validates and executes governed read models.
- **M2M Security / AaramIdentity:** Internal physical transport and authentication boundaries remain exactly as established.
- **AI Gateway Abstraction:** Gemini remains an isolated provider; the architecture must not hard-code Gemini-specific concepts into Brain Core orchestration.

**6. Exact documents created.**
- `docs/02-brain-core/llm-assisted-context-planning.md` (Architecture Impact Report)
- `docs/02-brain-core/phase-1-12-impact-matrix.md` (Phase Impact Matrix)
- `docs/02-brain-core/context-engine-impact.md` (Context Engine changes)
- `00-project-context/GENERAL-NL-LLM-ASSISTED-CONTEXT-PLANNING-REVIEW.md` (This document)

**7. Exact documents modified.**
- `docs/02-brain-core/brain-core-architecture.md` (Added Cognitive Context Planner capability)
- `docs/10-implementation-plan/engineering-log.md` (Logged architecture review and blocked Phase 13)

**8. Any ADRs created/superseded.**
- Created `docs/09-decisions/ADR-008-llm-assisted-context-planning.md` to formally adopt the Hybrid Context Model (Predefined + Dynamic Discovery) and establish the Cognitive Planner layer.

**9. Revised architecture in one concise diagram.**
```text
User
  ↓
[NL Query]
  ↓
Cognitive Context Planner (LLM)  <-- *NEW* (Decomposes query, plans retrieval)
  ↓
[Dynamic Retrieval Plan / Predefined Request]
  ↓
Brain Core Context Assembler (Deterministic) <-- *EXTENDED* (Supports iterative merging)
  ↓
Semantic / Schema Gateway & Adapters
  ↓
Governed Read-Only APIs / DBs (AaramInventory)
  ↓
[Provenance-Tagged Evidence Package]
  ↓
Reasoning LLM (Synthesizes answer)
  ↓
Answer / Governed Action
```

**10. Revised phase sequence.**
The next phase is NO LONGER "Phase 13 — API Contract Design & Adapter Implementation".
The revised next phase is:
**Phase 13 (New) — Cognitive Context Planning & Dynamic Discovery Architecture** (Designing the Semantic Metadata structures, Iterative Context Assembly interfaces, and the formal `EvidencePackage` contract).
*Only after* that architecture is approved can we move to Adapter Implementation (now Phase 14).

**11. Exact next task.**
Review this architecture reassessment with the team/owner for approval. If approved, the next active task is to design the machine-readable `EvidencePackage` and the schema metadata contract that the Cognitive Planner will use to discover dynamic context.

**12. Confirmation that Phase 13 implementation was NOT started.**
Confirmed. Zero Python code was written. No APIs, databases, adapters, or Gemini calls were implemented. Phase 13 implementation is formally BLOCKED pending approval of this architecture review.
