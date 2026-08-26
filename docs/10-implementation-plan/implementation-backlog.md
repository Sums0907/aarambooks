# AaramBooks Implementation Backlog

## Purpose
Convert the approved AaramBooks conceptual and technical architecture into an actionable, sequenced execution backlog. This backlog honors the bounded contexts established in the architecture baseline: Brain Core provides intelligence, Intelligence Domains orchestrate, and Business Domains execute and own operational truth.

---

## 1. Milestone 0: Engineering Foundation

### Milestone 0A — Engineering Foundation Hardening
**Goal:** Prevent deployment inconsistencies, port collisions, and configuration conflicts.
- [ ] Implement Configuration Management Standard (Pydantic settings, `.env.example`).
- [ ] Implement Port Management Standard and Central Registry.
- [ ] Implement Docker Standards (Service names, overrides).
- [ ] Implement Database Isolation Standards (Schemas, users).
- [ ] Enforce Service Identity Standard (Unique, explicit naming).
- [ ] Enforce Environment Isolation Standard (Isolation & Promotion rules).
- [ ] Enforce Deployment Readiness Checklist.

### Milestone 0B — Brain Core Foundation
**Goal:** Establish the underlying infrastructure, code repositories, and pipelines before building intelligence.
- [ ] Initialize code repositories and CI/CD pipelines.
- [ ] Setup developer environments and mock business data endpoints.
- [ ] Define Internal API Protocol (gRPC/REST) for communication between Intelligence Domains and Brain Core.
- [ ] Define the logical Memory Framework schema and select/integrate appropriate commodity infrastructure for persistence (rather than building custom databases).

---

## 2. MVP-1 Scope (Initial Release)
The first production release focuses strictly on foundational intelligence and a highly scoped conversation domain.
1. **Brain Core Foundation:** Establishing the Model Gateway, Context Engine, and Memory Framework. (Action Engine deferred).
2. **Customer Context Foundation:** Read-only integrations with ShopDeck and AaramIdentity.
3. **Customer Query Intelligence Domain (Limited Scope):** Automating conversational support strictly for basic read-only queries (e.g., Order Status, Delivery Updates).

---

## 3. MVP-1 Implementation Phases & Build Sequence

### Phase 1.1: Context Engine Validation (First Intelligence Capability)
**Goal:** Prove that Brain Core can successfully read, fuse, and interpret operational truth.

**PREREQUISITE:** Obtain/verify authoritative ShopDeck API documentation or authentic raw API payload.

**BLOCKED:** 
- Concrete ShopDeck adapter implementation (Customer Profile, Order Status) is blocked until the identity/payload contract is verified. (Never assume phone number is the ShopDeck primary identifier or that CSV structure equals REST API structure).

**ALLOWED IN PARALLEL:**
- [ ] Build generic Context Engine aggregation, fusion logic, and provider abstractions that do not depend on undocumented ShopDeck behavior.
- [ ] Validate Context Engine output against synthetic test customer scenarios.

### Phase 1.2: Core Infrastructure & Gateway
**Goal:** Establish the foundation for AI inference and state memory.
- [ ] Implement Model Gateway abstraction layer (Aaram owns the contract/abstraction, while the underlying implementation may integrate an external/off-the-shelf gateway).
- [ ] Provision external AI providers.
- [ ] Connect Context Engine output to Model Gateway for grounded reasoning.

### Phase 1.3: Customer Query Intelligence (Read-Only Orchestration)
**Goal:** Build the specific state machine for conversational queries.
- [ ] Implement Customer Query Intelligence Session Manager (Aaram owns conversation/session semantics and orchestration, while messaging and session storage infrastructure may be external).
- [ ] Connect Session Manager to Memory Framework.
- [ ] Build intent parsing for Order Status and Delivery queries.
- [ ] Formulate read-only customer responses (Action Engine execution is out of scope).

---

## 4. MVP-2 Scope (Deferred)
The second release will expand scope and introduce execution capabilities.
1. **NDR Intelligence Domain:** Automating Non-Delivery Report resolution logic.
2. **Action Engine Execution:** Closing the loop by allowing Intelligence Domains to trigger operational changes in Business Systems (e.g., triggering refunds or delivery retries).
3. **Knowledge Engine & Complex Queries:** Support for return policies, product catalog queries, and damaged product complaints.

---

## 5. Dependencies
- **Data Availability:** ShopDeck APIs must be available and stable for Context Engine read access during MVP-1.
- **Vendor Selection:** Model Gateway cannot be finalized until specific LLM vendors are procured.
- **Communication Channels:** Aaram owns the Customer Query Intelligence boundary. Specific external communication providers (Voice/Chat channels) must be selected for implementation, but are replaceable integrations rather than architectural dependencies.

---

## 6. First Components to Build (MVP-1)
1. **Context Engine (ShopDeck Adapter):** The absolute first capability to validate; it grounds all future AI reasoning in operational truth.
2. **Model Gateway:** Essential prerequisite for reasoning capabilities.
3. **Memory Framework:** Required to store session state and multi-turn conversation context.

---

## 7. First Integrations Required (MVP-1)
1. **ShopDeck Orders API (Read-only):** To pull line items and delivery status.
2. **ShopDeck Customer API (Read-only):** To pull basic identity and profile truth.

---

## 8. Decisions

### Architectural Decisions (Required Before Development)
1. **Internal API Protocol:** Selecting between gRPC, REST, or message queues.

### Implementation / Technology Selections (Deferred to Implementation Phase)
The following are vendor/infrastructure selections, not architectural prerequisites. They should be finalized when the relevant implementation begins:
1. **Database Selection:** Physical persistence technology for the Memory Framework.
2. **External AI Providers:** Procurement of the foundational LLMs for the Model Gateway.
3. **Supported Channels:** Defining the specific intake communication provider (WhatsApp, Web, or Email).

---

## 9. Development Readiness Checklist
- [ ] Architecture baseline and design documents frozen and approved.
- [ ] API Contracts drafted and reviewed.
- [ ] Architectural Decisions resolved.
- [ ] Developer environments configured.
- [ ] CI/CD pipeline and code repositories initialized.
