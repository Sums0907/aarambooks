# AaramBooks AI Agent Onboarding Prompt

**Instructions for the User:** Copy and paste everything below the line into your first message to a new AI Agent. This guarantees they build the perfect context about the architecture, systems, and exact call flows before writing any code.

---

### **SYSTEM INCEPTION & DOMAIN CONTEXT**
Welcome to AaramBooks! We are building a state-of-the-art intelligent automation system for a premium D2C home decor and bedding brand (Aaram Homes). Our mission is to completely decouple the "intelligence" of the business from the "transactional operations." You are tasked with maintaining, extending, and operating within the **Aaram Brain**, the sovereign intelligence layer of our ecosystem.

To succeed here, you must understand our strict **4-Box Architecture**, our specific integrations, and how our VoiceBot (Priya) physically executes tasks like Non-Delivery Report (NDR) remediation.

Read through this entire document to build your working memory.

---

### **THE 4-BOX ARCHITECTURE**
The ecosystem is rigidly split into four abstract domains. Intelligence never leaks into Operations, and Operations never makes cognitive decisions.

1. **The Brain (Aaram Brain)**
   - The central nervous system. It holds no business data itself. It dynamically requests "evidence" from Business Systems, builds real-time context, plans actions (using LLMs), and dispatches directives to edge endpoints (like VoiceBots).
   - Core Components: `Context Engine` (builds context), `Action Engine` (decides what to do), and `Intelligence Domains` (specialized reasoning layers like NDR).

2. **AZM (Aaram Zameer Model)**
   - The abstract cognitive data model. It defines what a "Customer", "Product", or "Conversation" is *abstractly*, completely independent of how any database stores them.

3. **SABAQ**
   - The feedback and continuous learning loop (the brain's memory).

4. **Business Systems (BS)**
   - The transactional, operational source-of-truth endpoints. They own the databases. They do not think; they just store state and execute operations.
   - **ShopDeck**: The core order management system, fulfillment engine, and the owner of the NDR queue. ShopDeck derives analytics like "Product Category Intelligence" natively.
   - **Inventory**: The authoritative source for rich product attributes (SKU, color, material, MRP).
   - **Aaram Identity**: The zero-trust gateway. It issues M2M (Machine-to-Machine) JWT tokens. Brain *must* authenticate through Identity to talk to any Business System.
   - **Packing & Packing Android App**: The operational systems used by the warehouse floor to fulfill orders.

---

### **INTEGRATIONS & COMMUNICATION**
How the 4-box architecture talks to each other:
- **Zero-Trust Boundary:** The Brain does not have direct database access to ShopDeck or Inventory. Every request must be an HTTP API call authenticated by a service token from Aaram Identity.
- **Context Execution Adapters (CEM):** The Brain communicates with Business Systems using strictly defined Adapters (e.g., `ShopdeckCemAdapter`). It sends an `AbstractEvidenceRequest` to the Business System, which replies with a `BusinessEvidenceResponse`.
- **Read-Only ShopDeck MCP Server:** A separate Model Context Protocol (MCP) server exists explicitly for you (the AI Agent). It allows you to safely introspect ShopDeck's PostgreSQL schemas and run read-only analytical queries to understand data shapes, *without* hardcoding DB credentials into the Brain's production runtime.

---

### **THE NDR CALL FLOW (END-TO-END)**
One of our primary Intelligence Domains is the **NDR Engine** (Non-Delivery Report). When a courier (e.g., Delhivery) fails to deliver a package, here is the exact sequence of how Priya (the VoiceBot) intervenes:

1. **ShopDeck BS Sync:** ShopDeck continuously polls courier APIs, detects a failed delivery, and creates an entry in its own internal `ndr_queue`.
2. **Brain NDR Polling:** The Brain runs a background daemon (`ndr_queue_poller.py`). It asks ShopDeck (via `claim_ndr_work`) for the next available NDR task.
3. **Action Dispatch:** The Brain's `NDRDispatchOrchestrator` generates an `ActionRequest` and routes it to the NDR Intelligence Domain.
4. **Context Building (CCC Builder):** 
   - `ccc_builder.py` takes the AWB number and asks the adapters for evidence.
   - It fetches the `NDRShipmentContext` from ShopDeck (getting Order Facts, Action History, and `category_intelligence`).
   - It fetches rich product details from Inventory BS.
   - It fuses these into the massive, immutable `CustomerConversationContext` (CCC).
5. **Projection:** The CCC is heavily sanitized into a `CustomerConversationProjection`. Internal IDs are stripped. Strict safety policies (e.g., "Never invent a discount") are injected.
6. **Exotel Webhook Generation:**
   - The Brain prepares the payload for Exotel (`exotel_webhooks.py`). 
   - It generates a dynamic, localized Hindi greeting message using the specific ShopDeck-derived `product_category` (e.g., *"आपने जो Bedsheet order किया था..."*).
   - It serializes all necessary context into `session_constants`.
7. **Exotel VoiceBot Execution:** Priya executes the call natively on Exotel's telephony network, governed *entirely* by the rules injected into `session_constants`.
8. **Outcome Parsing & Writeback:** When the call ends, Exotel POSTs the raw transcript back to the Brain. `reply_parser.py` classifies the customer's intent (e.g., `RESCHEDULE`, identifying the exact date). The Brain then pushes this decision back to ShopDeck BS's queue via `update_queue_status`.

---

### **YOUR DIRECTIVES**
- **Sovereignty:** Never attempt to connect the Brain directly to a Postgres database.
- **Consumption:** The Brain *consumes* intelligence (like categories) from Business Systems. It does not invent its own heuristics if the Business System already owns the logic.
- **Traceability:** Before proposing an architecture change, always verify the current state of `ccc_contracts.py` and the respective Adapters.

**Acknowledge that you have read and understood this architecture, and let me know what task we are tackling today!**
