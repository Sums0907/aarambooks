# AaramBooks Brain Core — Authoritative Implementation Roadmap

**STATUS: FROZEN**

This document serves as the **AUTHORITATIVE execution roadmap** for the AaramBooks Brain Core. It supersedes all previous phase definitions.

**Critical Execution Rule:** Implementation agents must follow the phase boundaries exactly as outlined below. Agents must NOT redesign or reorder phases without an explicit, approved architectural decision.

---

## Strategic Implementation Rules (Build-vs-Buy)

- **BUILD / OWN:** Aaram Brain Core abstractions, Context Engine, Provider Registry, Context fusion semantics, Memory/Knowledge/Reasoning semantics, Action Engine boundaries, Domain Intelligence (NDR & Queries), and proprietary governance contracts.
- **BUY / USE:** LLM inference, physical databases, vector/retrieval infrastructure, session/cache infrastructure, model gateway infrastructure, and messaging/telephony channels.
- **Commodity Procurement:** Selecting and configuring databases, LLMs, and gateways is an external, parallel activity and must not be treated as proprietary Brain implementation.
- **External Integration:** Do not assume REST. Define provider adapters against approved external contracts. Operational truth belongs to external systems.

---

## COMPLETE PHASE EXECUTION MAP

#### **Phase 1: Core Semantic Contracts & Action Boundaries**
- **Phase ID:** Phase 1
- **Phase name:** Core Semantic Contracts & Action Boundaries
- **Objective:** Establish the mathematical data structures that dictate how Aaram Brain understands the world and how it requests actions.
- **Architectural capability:** Brain Core structural contracts, API contracts, Action Engine boundaries.
- **Exact prerequisites:** Architecture baseline and data model documentation approved.
- **Dependencies:** None.
- **Source docs:** `docs/04-data-models/*.md`, `docs/06-api-contracts/brain-core-api-contracts.md`, `docs/02-brain-core/action-engine.md`
- **Files MUST read:** `src/shared/context_contracts/__init__.py`
- **Files allowed to create:** `src/brain_core/models/*.py`, `src/brain_core/action_engine/contracts.py`
- **Files allowed to modify:** None.
- **Files MUST NOT modify:** Operational databases, `docs/` (except logs), external system code.
- **Exact implementation tasks:** Define Pydantic models for Customer, Order, Shipment, and Inventory contexts. Define abstract BaseModels for `ActionRequest` and `ActionResponse`.
- **Tests required:** Pytest suite asserting schema immutability and strict validation rules.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** 100% test coverage on pure Python schema validation.
- **Handoff requirements:** The rigid Python data definitions for all Brain Core data models.
- **Blockers:** None.
- **Status:** **READY**

#### **Phase 2: Context Engine & Provider Registry**
- **Phase ID:** Phase 2
- **Phase name:** Context Engine & Provider Registry
- **Objective:** Build the system that fetches operational truth from various sources and fuses it into a single intelligence context.
- **Architectural capability:** Context Engine, Provider Registry, Context fusion.
- **Exact prerequisites:** Phase 1 completion.
- **Dependencies:** Phase 1.
- **Source docs:** `docs/02-brain-core/context-engine.md`, `docs/02-brain-core/provider-registry-architecture.md`
- **Files MUST read:** Phase 1 schemas.
- **Files allowed to create:** `src/brain_core/context_engine/*.py`, `src/brain_core/registry/*.py`, `src/shared/context_contracts/capability.py`, `src/shared/context_contracts/source.py`
- **Files allowed to modify:** `src/brain_core/context_engine/__init__.py`
- **Files MUST NOT modify:** Logic belonging to Memory, Reasoning, or Action engines.
- **Exact implementation tasks:** Build the `ProviderRegistry` class. Build the `ContextAssembler` that aggregates data, resolves conflicts, and outputs a unified Context model.
- **Tests required:** Mock provider tests to prove fusion logic correctly aggregates fragmented mock data.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** Context Engine successfully fuses mock data into a unified schema.
- **Handoff requirements:** The fusion engine ready to receive real adapters.
- **Blockers:** None.
- **Status:** **READY**

#### **Phase 3: Cognitive Logical Abstractions**
- **Phase ID:** Phase 3
- **Phase name:** Cognitive Logical Abstractions
- **Objective:** Define the Aaram-owned intelligence boundaries (Memory, Knowledge, Reasoning, Decisions) before attaching physical commodity infrastructure.
- **Architectural capability:** Memory Framework, Knowledge Engine, Model Gateway abstraction, Decision Engine.
- **Exact prerequisites:** Phase 1 completion.
- **Dependencies:** Phase 1.
- **Source docs:** `docs/02-brain-core/memory-framework.md`, `docs/02-brain-core/knowledge-engine.md`, `docs/02-brain-core/ai-model-gateway.md`, `docs/02-brain-core/decision-engine.md`
- **Files MUST read:** Phase 1 schemas.
- **Files allowed to create:** `src/brain_core/memory/interfaces.py`, `src/brain_core/knowledge/interfaces.py`, `src/brain_core/gateway/interfaces.py`
- **Files allowed to modify:** None.
- **Files MUST NOT modify:** Any physical DB drivers, vendor SDKs.
- **Exact implementation tasks:** Create Python ABCs (Abstract Base Classes) for Memory Read/Write, Knowledge Search, and LLM Generation. Implement the pure logical Decision Engine tree schemas.
- **Tests required:** Mock interface compliance tests.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** Brain Core logic expects specific method signatures, completely decoupled from vendor SDKs.
- **Handoff requirements:** The internal interface contracts for commodity infrastructure.
- **Blockers:** None.
- **Status:** **READY**

#### **Phase 4: Internal Operational Integrations**
- **Phase ID:** Phase 4
- **Phase name:** Internal Operational Integrations
- **Objective:** Connect Brain Core to existing Aaram-owned business systems.
- **Architectural capability:** AaramInventory integration, AaramPacking integration.
- **Exact prerequisites:** Phase 2 completion.
- **Dependencies:** Phase 2.
- **Source docs:** `docs/06-api-contracts/business-adapter-contract-pattern.md`
- **Files MUST read:** Phase 2 Registry.
- **Files allowed to create:** `src/business_adapters/inventory/*.py`, `src/business_adapters/packing/*.py`
- **Files allowed to modify:** `requirements.txt`
- **Files MUST NOT modify:** The actual AaramInventory and AaramPacking source code/databases.
- **Exact implementation tasks:** Implement against the approved AaramInventory/AaramPacking integration contract; transport is implementation-specific and must not be assumed by the architecture. Map operational truth to Phase 1 Pydantic contexts. Register them with the Provider Registry.
- **Tests required:** Wiremock tests simulating internal API responses.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** Adapters successfully map internal business payload to Brain Core Context models.
- **Handoff requirements:** Live Context Providers for internal truth.
- **Blockers:** None.
- **Status:** **READY**

#### **Phase 5: External Intelligence Integrations**
- **Phase ID:** Phase 5
- **Phase name:** External Intelligence Integrations
- **Objective:** Fetch operational truth from external partners.
- **Architectural capability:** ShopDeck integration, Logistics/Courier integration.
- **Exact prerequisites:** Phase 2 completion, external API access.
- **Dependencies:** Phase 2, External Vendors.
- **Source docs:** `docs/05-integrations/*.md`
- **Files MUST read:** Phase 2 Registry.
- **Files allowed to create:** `src/business_adapters/shopdeck/*.py`, `src/business_adapters/courier/*.py`
- **Files allowed to modify:** None.
- **Files MUST NOT modify:** Brain Core logic.
- **Exact implementation tasks:** Build API adapters against approved external contracts. Register them with the Context Engine.
- **Tests required:** Strict payload validation tests.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** External APIs map successfully to `CustomerContext` and `ShipmentContext`.
- **Handoff requirements:** Live Context Providers for external truth.
- **Blockers:** 
   - **ShopDeck:** awaiting headless/M2M authentication and final production integration contract.
   - **Logistics/Courier:** awaiting identification and access to the authoritative delivery-attempt/NDR source.
- **Status:** **BLOCKED**

#### **Phase 6: External Dependency Track — Human/DevOps Procurement**
- **Phase ID:** Phase 6
- **Phase name:** External Dependency Track — Human/DevOps Procurement
- **Objective:** Procure physical SaaS/DB technologies to power Brain Core.
- **Architectural capability:** Vendor resolution (DB, LLM, Gateway, Session/Event Bus).
- **Exact prerequisites:** Phase 3 completion.
- **Dependencies:** Human Management.
- **Source docs:** `docs/09-decisions/technical-decision-register.md`
- **Files MUST read:** None.
- **Files allowed to create:** `.env` configs, IaC scripts.
- **Files allowed to modify:** `docker-compose.override.yml`
- **Files MUST NOT modify:** Source code.
- **Exact implementation tasks:** Create accounts, acquire API keys, provision clusters.
- **Tests required:** Connectivity tests.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** Human/DevOps.
- **Implementation-status ownership:** Human/DevOps.
- **Exit criteria:** Credentials for commodity infrastructure are available.
- **Handoff requirements:** Infrastructure connection strings.
- **Blockers:** Vendor selection.
- **Status:** **DEFERRED (Parallelizable Activity)**

#### **Phase 7: Intelligence Infrastructure Binding**
- **Phase ID:** Phase 7
- **Phase name:** Intelligence Infrastructure Binding
- **Objective:** Connect Phase 3 ABCs to Phase 6 vendors.
- **Architectural capability:** Memory Framework (physical), Knowledge Engine (physical), Model Gateway integration.
- **Exact prerequisites:** Phase 3 and Phase 6 completion.
- **Dependencies:** Phase 3, Phase 6.
- **Source docs:** `docs/02-brain-core/*.md`
- **Files MUST read:** Phase 3 Interfaces.
- **Files allowed to create:** `src/infrastructure/adapters/*.py`
- **Files allowed to modify:** `requirements.txt`
- **Files MUST NOT modify:** Phase 3 ABCs or Phase 1 schemas.
- **Exact implementation tasks:** Write concrete classes that implement the Phase 3 interfaces using specific vendor SDKs.
- **Tests required:** Integration tests querying the managed DBs and LLM gateways.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** Brain Core successfully persists state and queries an LLM via the gateway.
- **Handoff requirements:** A fully stateful, LLM-connected Brain Core.
- **Blockers:** Awaiting Phase 6 Procurement.
- **Status:** **BLOCKED**

#### **Phase 8: Domain Intelligence Orchestration**
- **Phase ID:** Phase 8
- **Phase name:** Domain Intelligence Orchestration
- **Objective:** Build the business-specific reasoning and intelligence loops.
- **Architectural capability:** Reasoning, NDR Intelligence, Customer Query Intelligence.
- **Exact prerequisites:** Phase 2 (Context Engine).
- **Dependencies:** Context Engine, Action Engine schemas.
- **Source docs:** `docs/03-intelligence-domains/`
- **Files MUST read:** Context schemas, Action schemas, Provider Registry.
- **Files allowed to create:** `src/intelligence_domains/ndr/*.py`, `src/intelligence_domains/customer_query/*.py`
- **Files allowed to modify:** None.
- **Files MUST NOT modify:** Brain Core logic, Business Adapters.
- **Exact implementation tasks:** Implement the exact orchestration loops: Fetch Context -> Apply Rules -> Evaluate Decision -> Formulate ActionRequest. 
- **Tests required:** E2E tests simulating user inputs and verifying the resulting `ActionRequest` using deterministic synthetic/frozen fixtures.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** The Intelligence Domains generate safe, correct `ActionRequests` for NDR and Query flows against synthetic inputs.
- **Handoff requirements:** Verified intelligence orchestration logic.
- **Blockers:** Real-world integration validation is blocked pending Phase 5 & 7. Development/Unit-Testing is NOT blocked.
- **Status:** **READY (for Synthetic Development)** / **BLOCKED (for Real-World Validation)**

#### **Phase 9: Ecosystem Communication & Governance**
- **Phase ID:** Phase 9
- **Phase name:** Ecosystem Communication & Governance
- **Objective:** Manage inbound/outbound event boundaries and security.
- **Architectural capability:** Event contracts/integration, Security and governance.
- **Exact prerequisites:** Phase 8 completion.
- **Dependencies:** Phase 8, Event bus infrastructure.
- **Source docs:** `docs/07-events/`, `docs/08-security-governance/`
- **Files MUST read:** `src/brain_core/action_engine/contracts.py`
- **Files allowed to create:** `src/event_bus/*.py`, `src/security/*.py`
- **Files allowed to modify:** None.
- **Files MUST NOT modify:** Intelligence Domain reasoning loops.
- **Exact implementation tasks:** The architecture requires governed event/API boundaries; the physical event-bus technology remains a commodity implementation choice. Implement generic intake endpoints and outbound dispatchers enforcing strict schema/security guardrails.
- **Tests required:** E2E security boundary tests.
- **Documentation updates:** `engineering-log.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** Complete isolation between Intelligence Domains and external networks via governed API boundaries.
- **Handoff requirements:** A production-ready API boundary.
- **Blockers:** Physical binding to specific event infrastructure.
- **Status:** **READY (Logical Boundaries)** / **BLOCKED (Physical Binding)**

#### **Phase 10: Testing, Certification & Production Hardening**
- **Phase ID:** Phase 10
- **Phase name:** Testing, Certification & Production Hardening
- **Objective:** Ensure the system is safe for production.
- **Architectural capability:** Testing/certification, Production hardening.
- **Exact prerequisites:** Completion of all prior phases.
- **Dependencies:** All prior phases.
- **Source docs:** `docs/10-implementation-plan/engineering-foundation-standard.md`
- **Files MUST read:** Entire codebase.
- **Files allowed to create:** `tests/e2e/*.py`
- **Files allowed to modify:** `Dockerfile`, `docker-compose.yml`, GitHub Actions.
- **Files MUST NOT modify:** Core architectural schemas.
- **Exact implementation tasks:** Chaos testing, token budget logging, latency profiling, environment promotion configuration.
- **Tests required:** Full E2E regression suite.
- **Documentation updates:** `implementation-roadmap-governance.md`
- **Engineering-log ownership:** AI Agent executing the phase.
- **Implementation-status ownership:** AI Agent executing the phase.
- **Exit criteria:** Zero severity-1 vulnerabilities, 100% strict contract adherence.
- **Handoff requirements:** Production images.
- **Blockers:** Completion of all phases.
- **Status:** **BLOCKED**

---

## DEPENDENCY ANALYSIS

**1. Dependency Graph**
- `[Phase 1]` → `[Phase 2]`, `[Phase 3]`
- `[Phase 2]` → `[Phase 4]`, `[Phase 5]`
- `[Phase 2]`, `[Phase 3]` → `[Phase 8 (Synthetic Dev)]` 
- `[Phase 8 (Synthetic Dev)]` → `[Phase 9 (Logical Dev)]`
- `[Phase 6 (External Procurement)]` → `[Phase 7]`, `[Phase 9 (Physical Binding)]`
- `[Phase 5]`, `[Phase 7]` → `[Phase 8 (Real-World Validation)]`
- `[Phase 8]`, `[Phase 9]` → `[Phase 10]`

**2. Parallelizable Phases**
Phases 1, 2, 3, 4, 8 (Synthetic), and 9 (Logical) can be implemented in a rapid, decoupled sequence or overlapping tracks. Phase 6 (Procurement) runs entirely in parallel in the background.

**3. Synthetic Fixture Rules**
- **Phase 8 (Domain Intelligence):** Must fully implement Reasoning, NDR Rules, and Query Intents using deterministic, frozen JSON fixtures representing `CustomerContext` and `ShipmentContext`.
- **Phase 2 (Context Engine):** Must test context fusion logic using deterministic mock responses injected into the Provider Registry.

---

## HISTORICAL CONTEXT & COMPLETED FOUNDATIONS

*This section preserves the original project setup requirements for historical reference. The phases above supersede the legacy MVP-1 sequence.*

- **Milestone 0A — Engineering Foundation Hardening:** Focused on preventing deployment inconsistencies, port collisions, and configuration conflicts. Includes Raw Data Protection Standard enforcement via `.gitignore` and `pre-commit` hooks.
- **Development Readiness Checklist:**
  - [x] Architecture baseline and design documents frozen and approved.
  - [x] API Contracts drafted and reviewed.
  - [x] Architectural Decisions resolved (Commodity choices deferred).
  - [x] Developer environments configured.
  - [x] CI/CD pipeline and code repositories initialized.
- **ShopDeck Investigation (Completed):** Discovered that the ShopDeck MCP relies on 3-legged interactive OAuth and lacks NDR event datasets. Backend integration must use REST/gRPC once headless authentication is secured.
