# Inventory Intelligence Domain: Architecture Readiness

## 1. Current ID Architecture
The current `Inventory Intelligence Domain` (`src/intelligence_domains/inventory_intelligence/`) is a simple, synchronous RAG/Q&A wrapper. It consists of:
- `orchestrator.py`: A stateless wrapper that passes natural language strings to the Brain Core orchestration layer and uses the `ModelGatewayProvider` to format a conversational response.
- `knowledge.py`: A stub that passes semantic concept search queries to the generic `AzmProvider`.

## 2. Existing Reusable Brain Core Infrastructure
Based on repository inspection, Brain Core provides the following certified abstractions ready for domain use:
- **LLM/Reasoning:** `ModelGatewayProvider` (implemented via `LiteLLMGatewayAdapter`)
- **Memory/Case State:** `MemoryProvider` (implemented via `PgVectorMemoryAdapter`)
- **Knowledge/Semantic Rules:** `AzmProvider` (implemented via `PgVectorKnowledgeAdapter`)
- **Context/Evidence:** `ContextCapabilityGateway`, `ContextAssembler`, `EvidenceRequirement`, `SemanticConstraint`
- **Action Engine:** `ActionRequest`, `ActionCategory` (contracts exist in `src/brain_core/action_engine/contracts.py`)
- **Decision Engine:** `DecisionRecommendation`, `DecisionAnalysisRequest` (interfaces exist in `src/brain_core/decision/interfaces.py`)

## 3. Seven-Gap Classification

1. **Domain Orchestrator & Case Management:** `EXISTING` (Can be implemented by consuming `MemoryProvider`).
2. **Semantic Requirements Engine:** `EXTEND` (ID needs to parse intents using `ModelGatewayProvider` to explicitly build existing `EvidenceRequirement` objects).
3. **Domain-Specific Knowledge & Policies:** `EXISTING` (Can be consumed via `AzmProvider`).
4. **Resolution & Decision Intelligence:** `EXISTING` (Contracts exist in `src/brain_core.decision.interfaces`).
5. **Action Formulation:** `EXISTING` (Contracts exist in `src.brain_core.action_engine.contracts`).
6. **Escalation Intelligence:** `EXISTING` (`ActionCategory.HUMAN_ASSISTANCE` provides the escalation route).
7. **Outcome Tracking & Memory:** `EXISTING` (`MemoryProvider` can persist historical case outcomes).

## 4. Exact Dependency Graph
- **Inventory Intelligence** consumes:
  - `src.brain_core.gateway.interfaces.ModelGatewayProvider` (Reasoning & Intent Parsing)
  - `src.brain_core.memory.interfaces.MemoryProvider` (Case Management & Outcome Tracking)
  - `src.shared.azm.interfaces.AzmProvider` (Domain Policies)
  - `src.brain_core.context_engine.assembler.ContextAssembler` (Evidence Gathering)
  - `src.brain_core.decision.interfaces` (Structured Decisions)
  - `src.brain_core.action_engine.contracts` (Actions & Escalations)

## 5. Ownership Boundaries
- **Inventory Intelligence (ID)** owns domain interpretation, determining required evidence, business logic reasoning, decision-making, escalation risk assessment, and action formulation.
- **Brain Core** owns the underlying LLM gateway, PostgreSQL memory/knowledge persistence, dynamic capability routing, generic context structures, and action/decision definitions.
- **AaramInventory** owns physical inventory database schemas, ORM logic, and truth persistence (shielded behind the CEM boundary).

## 6. Required New Files
- `src/intelligence_domains/inventory_intelligence/decisions.py` (Domain-specific structured decision mapping)
- `src/intelligence_domains/inventory_intelligence/actions.py` (Domain-specific action request formatters)
- `src/intelligence_domains/inventory_intelligence/escalation.py` (Risk evaluation thresholds)

## 7. Required Modified Files
- `src/intelligence_domains/inventory_intelligence/orchestrator.py` (Refactor to be stateful, invoke memory, explicit semantic planning, and yield decisions/actions).
- `src/intelligence_domains/inventory_intelligence/knowledge.py` (Expand to pull SOPs from Azm).
- `tests/intelligence_domains/inventory_intelligence/test_orchestrator.py` (Update test harnesses).

## 8. Files That Must NOT Be Modified
- `src/main.py`
- `src/infrastructure/context_capability_gateway.py`
- `src/brain_core/context_engine/assembler.py`
- `src/shared/cognitive_planning_contracts.py`
- `src/shared/semantic_resolution_contracts.py`
- Legacy systems and physical models.

## 9. Proposed Implementation Sequence
1. Refactor `orchestrator.py` to maintain case state via `MemoryProvider` (Gap 1).
2. Upgrade `orchestrator.py` to intercept raw queries, invoke `ModelGatewayProvider` for intent parsing, and construct precise `EvidenceRequirement` structures for the `ContextAssembler` (Gap 2).
3. Connect `knowledge.py` to pull and inject SOPs into the LLM prompts (Gap 3).
4. Implement structured output handling for `DecisionRecommendation` (Gap 4).
5. Map structured decisions into `ActionRequest` formulations, including `HUMAN_ASSISTANCE` escalations (Gap 5 & 6).
6. Wrap the orchestrator lifecycle to commit the final outcome to `MemoryProvider` (Gap 7).

## 10. Blockers
**None.** No dependencies are blocked. All required infrastructure contracts are present in Brain Core.

## 11. Architectural Decisions Requiring User Approval
- Confirm that actions formulated by the ID (`ActionRequest`) should be yielded back to the `InboundReceiver`/`EventBus` for physical dispatch, rather than ID implementing a physical HTTP webhook dispatcher internally.

**STATUS:** ID is READY FOR IMPLEMENTATION.

---

### Answers to Required Questions (Repository Evidence):
1. **How should ID maintain case/conversation state?** Via `MemoryProvider.write_memory()` and `read_memory()` using a unique `session_id`.
2. **Does the existing Memory Framework already provide this?** Yes, `PgVectorMemoryAdapter` implements `MemoryProvider`.
3. **How should ID formulate EvidenceRequirements?** By interpreting intents (via Gateway) and creating `EvidenceRequirement` objects manually.
4. **Which existing LLM/reasoning abstraction should ID use?** `ModelGatewayProvider` (`LiteLLMGatewayAdapter`).
5. **Does a Decision Engine already exist?** Yes, interfaces are at `src.brain_core.decision.interfaces`.
6. **Does an Action Engine already exist?** Yes, contracts are at `src.brain_core.action_engine.contracts`.
7. **What is the existing ActionIntent contract?** `ActionRequest` mapping to `ActionCategory`.
8. **Where should actions be dispatched?** Via the generic orchestration entry point or `EventBus`.
9. **Does an escalation mechanism already exist?** Yes, `ActionCategory.HUMAN_ASSISTANCE`.
10. **How should ID record outcomes?** `MemoryProvider.write_memory()`.
11. **What existing Knowledge Engine/semantic knowledge mechanisms are available?** `AzmProvider` (`PgVectorKnowledgeAdapter`).
12. **Which of the seven gaps can be implemented entirely inside ID?** All seven.
13. **Which gaps require another Brain Core subsystem first?** None.
