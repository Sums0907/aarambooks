# Phase 8 Readiness Audit: Domain Intelligence Orchestration

## 1. AUTHORITATIVE PHASE 8 PURPOSE
Build the business-specific reasoning and intelligence loops that orchestrate the resolution of NDRs (Non-Delivery Reports) and Customer Queries, isolating these domain-specific workflows from the generic Aaram Brain Core while leveraging its cognitive abstractions.

## 2. EXACT PHASE 8 OBJECTIVES
- Implement the NDR orchestration lifecycle (Context Assembly -> Failure Reason Understanding -> Resolution Decision -> Action Request Formulation).
- Implement the Customer Query orchestration lifecycle (Query Intake -> Context Assembly -> Intent Understanding -> Response/Resolution Decision -> Action Request Formulation).
- Establish the specialized intelligence logic (Reasoning, Decisions, Intent Classification) inside `src/intelligence_domains/` without altering generic Brain Core components or business domain truth.
- Validate orchestration logic using deterministic, frozen synthetic fixtures.

## 3. EXACT TASKS
- Create `src/intelligence_domains/ndr/` module and implement NDR Case Management, Resolution Intelligence, and Escalation Intelligence.
- Create `src/intelligence_domains/customer_query/` module and implement Query Intake, Intent Intelligence, and Conversation Intelligence.
- Wire these intelligence loops to utilize the `ContextAssembler`, Phase 3 logical interfaces (`ModelGatewayProvider`, `KnowledgeProvider`), and `ActionEngine` schemas.
- Write E2E tests simulating user/logistics inputs against frozen synthetic `CustomerContext` and `ShipmentContext` fixtures, asserting on the correct `ActionRequest` generation.

## 4. EXACT FILES TO CREATE
- `src/intelligence_domains/ndr/*.py` (e.g., orchestrator, resolution, intents)
- `src/intelligence_domains/customer_query/*.py` (e.g., orchestrator, intents, responses)
- `tests/intelligence_domains/ndr/*.py`
- `tests/intelligence_domains/customer_query/*.py`
- Synthetic frozen JSON fixtures (e.g., `tests/fixtures/synthetic_contexts.json`)

## 5. EXACT FILES TO MODIFY
- `docs/10-implementation-plan/engineering-log.md` (to record execution progress).
- No source files (`src/*`) are permitted to be modified.

## 6. FILES THAT MUST REMAIN UNTOUCHED
- Brain Core logic (`src/brain_core/*`)
- Business Adapters (`src/business_adapters/*`)
- Core architectural schemas (`src/shared/context_contracts/*`)
- Infrastructure integrations (`src/infrastructure/*`)
- Generic Phase 3 cognitive interfaces.

## 7. DEPENDENCIES FROM PHASES 1–7
- Phase 1: Context models and Action boundaries (`ActionRequest`, `ActionResponse`).
- Phase 2: `ContextAssembler` and `ProviderRegistry`.
- Phase 3: Cognitive logical abstractions (`ModelGatewayProvider`, `MemoryProvider`, `KnowledgeProvider`, `DecisionProvider`).
- Phase 7: Functional infrastructure bindings (LiteLLM, PgVector) available via dependency injection.

## 8. WHAT CAN BE DONE SYNTHETICALLY (AUTHORIZED NOW)
- Implementation of the entire orchestration logic, reasoning prompts, intent classification, and decision trees within the intelligence domains.
- E2E testing against frozen JSON mock contexts (`CustomerContext`, `ShipmentContext`, `InventoryContext`) that mimic what the Context Engine would output.
- Asserting that the intelligence loops successfully generate the expected `ActionRequest` and conversational responses.

## 9. WHAT MUST REMAIN DEFERRED
- Real-world validation against live Shiprocket/ShopDeck data feeds (BLOCKED pending physical event binding).
- Live physical transport integration (e.g., live webhook listeners, Kafka consumers, operational API integration).
- Integration into operational helpdesk systems or telephony providers.

## 10. EXPLICIT PHASE 9+ WORK THAT MUST NOT BE DONE
- Do not build inbound/outbound event boundaries (API intake endpoints, webhook receivers, event bus dispatchers).
- Do not build authentication wrappers for intelligence endpoints.
- Do not configure production deployment orchestration, cron jobs, or real-time queuing systems.
- Do not deploy physical transport infrastructure.

## 11. TESTING/VALIDATION REQUIREMENTS
- Comprehensive E2E tests simulating user inputs (queries) and logistics inputs (NDR events).
- Verification that the generated `ActionRequest` objects strictly adhere to deterministic synthetic/frozen fixtures.

## 12. PHASE 8 COMPLETION CRITERIA
- The Intelligence Domains successfully generate safe, correct `ActionRequests` for NDR and Query flows against synthetic inputs.
- All intelligence logic is strictly confined to `src/intelligence_domains/`.
- Zero modifications are made to Brain Core logic or Business Adapters.
- The 56/56 existing tests remain passing.
