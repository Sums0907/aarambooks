# Open Decisions Register

This register formally tracks architectural, implementation, and business decisions for the AaramBooks ecosystem. It clarifies which structural principles are locked (CLOSED) and which technology/business details remain unresolved (OPEN).

---

## 1. CLOSED ARCHITECTURAL DECISIONS

These decisions are formally closed based on the foundational AaramBooks architecture principles. They establish strict boundaries that must not be violated during implementation.

### DEC-001: Customer Context Ownership
- **Status:** CLOSED
- **Decision Statement:** Operational customer truth remains strictly owned by Business Domain Systems (e.g., AaramIdentity, ShopDeck). Aaram Brain owns derived intelligence context only.
- **Reasoning:** Aaram Brain must not become a duplicate customer master database (CRM). Duplicating operational truth creates synchronization risks and violates bounded contexts.
- **Architectural Impact:** The Context Engine dynamically retrieves customer master data (e.g., identity, explicit account details). The Brain Core Memory Framework only stores intelligence context (e.g., inferred preferences, interaction history) and never acts as the system of record for the customer profile.

### DEC-002: Conversation Context Ownership
- **Status:** CLOSED
- **Decision Statement:** Raw conversation records, conversation intelligence, and multi-turn semantic memory are owned by Intelligence Domains and the Brain Core Memory Framework. However, conversation intelligence must never become operational customer truth.
- **Reasoning:** Unstructured conversation history and derived AI insights are transient and probabilistic. They must remain isolated from the rigid, deterministic operational records.
- **Architectural Impact:** Customer conversations are tracked by Customer Query Intelligence and stored in the Memory Framework. They are not written into operational business databases, although discrete execution outcomes (e.g., "refund requested") are.

### DEC-003: Knowledge Ownership
- **Status:** CLOSED
- **Decision Statement:** Business Domains own the authoritative business knowledge content (e.g., product details, return policies, SOPs). Brain Core's Knowledge Engine owns the understanding, retrieval, and intelligence capabilities over that content.
- **Reasoning:** Aaram Brain must not become a duplicate Content Management System (CMS) or policy master.
- **Architectural Impact:** The Knowledge Engine dynamically indexes, embeds, and retrieves policies owned by external systems. It does not author or own the policies.

### DEC-004: AI Decision Authority
- **Status:** CLOSED
- **Decision Statement:** AI (Aaram Brain) produces recommendations and issues controlled action requests. Business Domain Systems retain absolute execution authority for operational changes.
- **Reasoning:** Business systems must evaluate all requested actions against deterministic business rules to ensure compliance, safety, and inventory correctness.
- **Architectural Impact:** Intelligence Domains (NDR, Customer Query) use the Action Engine to dispatch requests via API contracts. They cannot directly alter the databases of ShopDeck, AaramInventory, or AaramPacking.

### DEC-005: Human Escalation Principle
- **Status:** CLOSED
- **Decision Statement:** AI should recommend escalation to a human when AI confidence is low, policies dictate manual review, risk is high, or negative customer sentiment requires human empathy.
- **Reasoning:** Aaram Brain is an intelligence orchestrator, not a helpdesk ticketing platform. Support workflow execution belongs to operational support systems.
- **Architectural Impact:** Intelligence Domains flag cases for escalation and hand them off. They do not manage the human agent queues, ticket assignment, or internal support workflows.

---

## 2. OPEN IMPLEMENTATION DECISIONS

These physical implementation and technology decisions are intentionally deferred until the engineering build phase.

- **Database Selection (Memory Framework):**
  - *Why Deferred:* The physical database technology (e.g., Vector DB for embeddings, NoSQL for conversation history) requires data modeling and infrastructure planning.
- **Internal API Protocol:**
  - *Why Deferred:* Choosing between gRPC, REST, or message queues for communication between Intelligence Domains and Brain Core depends on latency and event-driven architecture requirements.
- **External AI Providers:**
  - *Why Deferred:* Selecting specific vendors (OpenAI, Anthropic, Gemini, etc.) for LLMs, STT, and TTS is an implementation procurement decision, abstracted by the Model Gateway.
- **Supported Channels:** (e.g., WhatsApp, Email, Web Chat).
  - *Why Deferred:* Requires business prioritization and implementation scoping based on customer demographic preferences.
- **Voice/Chat/Email Architecture:**
  - *Why Deferred:* Physical infrastructure choices (e.g., SIP integrations, webhook routing) depend on vendor evaluation and channel selection.
- **Telephony Provider Selection:**
  - *Why Deferred:* Selecting the physical provider (e.g., Twilio, Exotel) for voice outreach is a vendor procurement decision.
- **Human Support Ticketing System:**
  - *Why Deferred:* Selecting the specific helpdesk software (e.g., Zendesk, Freshdesk) is an IT procurement decision, not an architectural baseline principle.
- **AI Evaluation Framework:**
  - *Why Deferred:* The exact statistical models, guardrails, and telemetry tooling used to measure baseline intent accuracy require further engineering discovery.
- **Real-Time Response Requirements:**
  - *Why Deferred:* Latency SLAs for synchronous chat versus asynchronous email require infrastructure capacity planning and business alignment.

---

## 3. FUTURE BUSINESS DECISIONS

These decisions require strategic input from business stakeholders before technical implementation can finalize specific rules.

- **Automation Approval Levels:** Determining financial thresholds where AI is allowed to auto-approve refunds or replacements without human-in-the-loop (HITL) approval.
- **Customer Communication Policies:** Defining the exact brand voice, tone, and acceptable phrasing for automated responses.
- **Support Operating Model:** Defining how human agents will interact with escalated AI tickets and the required team structure.
