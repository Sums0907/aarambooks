# AaramBooks Implementation Backlog

## Purpose
Convert the approved AaramBooks conceptual and technical architecture into an actionable, sequenced execution backlog. This backlog honors the bounded contexts established in the architecture baseline: Brain Core provides intelligence, Intelligence Domains orchestrate, and Business Domains execute and own operational truth.

---

## 1. MVP Scope (Phase 1)
The initial production release focuses on foundational intelligence and two specific high-value problem domains:
1. **Brain Core Foundation:** Establishing the Model Gateway, Context Engine, Memory Framework, and Action Engine.
2. **Customer Context Foundation:** Read-only integration with ShopDeck and AaramIdentity.
3. **NDR Intelligence Domain:** Automating Non-Delivery Report resolution logic.
4. **Customer Query Intelligence Domain:** Automating conversational support for orders, delivery, products, and returns.

---

## 2. Implementation Phases & Build Sequence

### Phase 1.1: Core Infrastructure & Gateway
**Goal:** Establish the foundation for AI inference, state memory, and internal routing.
- [ ] Implement Model Gateway abstraction layer.
- [ ] Provision external AI providers (LLM provider selected from Open Decisions).
- [ ] Deploy initial Memory Framework database (Technology selected from Open Decisions).
- [ ] Establish foundational API Contracts (gRPC/REST) between Brain Core and domain boundaries.

### Phase 1.2: Business System Integrations (Read-Only)
**Goal:** Enable Brain Core's Context and Knowledge Engines to fetch operational truth.
- [ ] Implement ShopDeck API Integrations (Customer Profile, Order Status, Product Catalog).
- [ ] Implement Logistics API Integrations (Shipment statuses for NDRs).
- [ ] Build Context Engine aggregation and fusion logic.

### Phase 1.3: Intelligence Domains (Orchestration)
**Goal:** Build the specific state machines and domain logic for the MVP scopes.
- [ ] Implement NDR Intelligence State Model (Intake, Contextual Understanding, Resolution Recommendation).
- [ ] Implement Customer Query Intelligence Session Manager (Multi-turn conversational tracking).
- [ ] Implement Knowledge Engine retrieval logic over static business rules (Policies, SOPs).
- [ ] Implement Reasoning & Decision Engine recommendation pathways.

### Phase 1.4: Action Execution & Feedback
**Goal:** Close the loop by allowing Intelligence Domains to trigger operational changes.
- [ ] Build Action Engine request formatter (Standardized intent payloads).
- [ ] Implement Business Domain Validation (e.g., ShopDeck receiving and validating a refund request).
- [ ] Implement Outcome Intelligence (Feedback loop logging resolutions back to the Memory Framework).

---

## 3. Dependencies
- **Data Availability:** ShopDeck and Logistics APIs must be available and stable for Context Engine read access.
- **Vendor Selection:** Model Gateway cannot be finalized until the specific LLM vendors are procured.
- **Communication Channels:** Customer Query Intelligence requires the Voice/Chat channel architecture to be finalized to build the intake layer.

---

## 4. First Components to Build
1. **Model Gateway:** Essential prerequisite for any reasoning or intent parsing capabilities.
2. **Context Engine (ShopDeck Adapter):** Required to provide grounding operational truth to the reasoning models.
3. **Memory Framework:** Required to store session state and multi-turn conversation context.

---

## 5. First Integrations Required
1. **ShopDeck Orders API (Read-only):** To pull line items and delivery status.
2. **ShopDeck Customer API (Read-only):** To pull basic identity and profile truth.
3. **Courier/Logistics Webhooks (Read-only):** To ingest inbound NDR events.

---

## 6. Technical Decisions to Close Before Development
Before coding begins, the following open decisions must be formally closed:
1. **Database Selection:** Physical database for the Memory Framework (e.g., Vector DB for embeddings, NoSQL for session state).
2. **Internal API Protocol:** Selecting between gRPC, REST, or message queues for communication between Intelligence Domains and Brain Core.
3. **External AI Providers:** Procurement of the foundational LLM (OpenAI, Anthropic, Gemini, etc.) for the Model Gateway.
4. **Supported Channels:** Defining the initial intake channel (WhatsApp, Web, or Email) to build the intake adapters.

---

## 7. Development Readiness Checklist
- [ ] Architecture baseline and design documents frozen and approved.
- [ ] API Contracts (Brain Core, Business Systems, Intelligence Domains) drafted and reviewed.
- [ ] Technical Decisions to Close Before Development resolved.
- [ ] Developer environments configured (Access to mock ShopDeck/Logistics APIs).
- [ ] CI/CD pipeline and code repositories initialized.
- [ ] Model Gateway API keys secured and provisioned.
