# NDR Intelligence Integration Architecture & Boundaries

## 1. Purpose & Integration Philosophy

This document defines the conceptual integration architecture and relationship boundaries between the **NDR Resolution Intelligence Domain (NDR-ID)**, authoritative business systems, customer communication channels, operational support tools, and Aaram Brain Core.

### Core Integration Principles:
1. **Zero Ownership Transfer:** Integrations enable context ingestion and recommendation delivery without shifting operational truth or execution ownership into the intelligence domain.
2. **Abstracted Communication:** NDR-ID reasons over semantic communication intents rather than concrete telephony protocols or messaging vendor SDKs.
3. **Governed Action Interfaces:** All outgoing resolution proposals flow through governed action boundaries ensuring policy compliance, auditable provenance, and human-in-the-loop safeguards.
4. **Decoupled Architecture:** Business systems and carrier integrations may refactor internal schemas and vendor APIs without altering the core reasoning capabilities of NDR-ID.

---

## 2. Conceptual Integration Topology

```
                                  ┌─────────────────────────────────────────┐
                                  │     SHARED INTELLIGENCE FOUNDATION      │
                                  │   (Aaram Brain Core & Global Azm)       │
                                  │  • Context Planning  • Reasoning Engine │
                                  │  • Semantic Vocab    • Memory / Learning│
                                  └────────────────────┬────────────────────┘
                                                       │ Shared AI Machinery
                                                       ▼
┌────────────────────────────────┐        ┌─────────────────────────────────┐        ┌────────────────────────────────┐
│     BUSINESS TRUTH SYSTEMS     │        │          NDR-ID DOMAIN          │        │     LOGISTICS & 3PL SYSTEMS    │
│  (ShopDeck / Orders / Identity)│        │   (Resolution Intelligence)     │        │  (Carrier Tracking & Dispatch) │
│                                │        │                                 │        │                                │
│  • Reads: Order, Customer,     │◄───────┤  • Failure Diagnosis            ├───────►│  • Ingests Delivery Exceptions │
│    Shipment, & Payment state   │        │  • Priority & Risk Assessment   │        │  • Recommends Reattempts       │
│  • Emits: Action Proposals     │        │  • Strategy & Playbook Selection│        │  • Recommends Carrier Disputes │
└────────────────────────────────┘        └────────────┬────────┬───────────┘        └────────────────────────────────┘
                                                       │        │
                                   Conversational Flow │        │ Escalation Context
                                                       ▼        ▼
                                  ┌────────────────────┴──┐  ┌──┴───────────────────┐
                                  │ CUSTOMER CHANNELS     │  │ HUMAN SUPPORT SYSTEMS │
                                  │ (WhatsApp, IVR, SMS)  │  │ (Care Queue, Desk UI) │
                                  │                       │  │                      │
                                  │ • Intent Discovery    │  │ • Concierge Triage   │
                                  │ • Preference Capture  │  │ • Exception Handling │
                                  └───────────────────────┘  └──────────────────────┘
```

---

## 3. Boundary Relationships

### 3.1 Business Truth Systems (ShopDeck / Orders / Customers)
- **Nature of Relationship:** Consumer of authoritative operational truth; producer of governed business actions.
- **Inbound Context:** Reads published projections of customer details, order line items, transaction totals, payment modes (COD vs Prepaid), and historical shipment statuses.
- **Outbound Guidance:** Emits structured action recommendations (e.g. update delivery date, modify shipping address landmark, apply retention incentive).
- **Invariant:** NDR-ID never alters customer records, order amounts, or financial ledgers directly.

### 3.2 Logistics & Carrier Execution Systems (3PL / Courier Networks)
- **Nature of Relationship:** Ingestion of operational failure signals; recommendation of courier reattempts and claims.
- **Inbound Signals:** Ingests courier failure scan events (e.g. customer unavailable, incomplete address, delivery rescheduled, rejected, damaged).
- **Outbound Guidance:** Recommends formal reattempt instructions, preferred delivery time slots, enriched delivery instructions, or formal carrier dispute tickets.
- **Invariant:** NDR-ID does not maintain direct socket connections to couriers or bypass business system logistics gateways.

### 3.3 Customer Communication Channels (WhatsApp, IVR, SMS)
- **Nature of Relationship:** Interactive touchpoint for intent discovery and preference collection.
- **Role:** Presents structured choices to the customer (e.g., date selection buttons, landmark input, digital payment options) and captures inbound responses.
- **Channel Fallback Intelligence:** Dynamically selects optimal outreach channels based on urgency, customer profile, and time sensitivity (e.g., immediate interactive messaging followed by voice call fallback).
- **Invariant:** Channel adapters handle physical telephony and messaging protocols; NDR-ID handles conversational reasoning and intent extraction.

### 3.4 Operational Support & Human Concierge Systems
- **Nature of Relationship:** Handoff interface for complex, high-risk, or disputed delivery exceptions.
- **Outbound Context:** Packages rich chronological context, customer sentiment summaries, diagnosed failure reasons, and recommended talking points for support agents.
- **Inbound Feedback:** Ingests human agent resolution notes and outcome decisions to feed the outcome evaluation and learning loop.
- **Invariant:** Human operators always retain override authority over automated intelligence recommendations.

### 3.5 Aaram Brain Core & Global Azm
- **Nature of Relationship:** Domain specialist to shared intelligence foundation.
- **Capabilities Leveraged:**
  - *Context Engine:* Federates multi-system evidence into a unified context container.
  - *Knowledge Engine (Azm):* Supplies semantic concepts, policy constraints, and domain terminology.
  - *Reasoning & Decision Engines:* Evaluates multi-factor scenarios and generates confidence-scored recommendations.
  - *Memory Framework:* Retains resolution histories and stores outcome feedback for continuous model improvement.
- **Invariant:** NDR-ID contains domain-specific recovery strategies; Brain Core remains 100% domain-agnostic.

---

## 4. Integration Invariants & Governance Summary

| Integration Point | Invariant Enforced |
| :--- | :--- |
| **Operational Data Access** | All data access is read-only via published business projections. Direct table mutation is strictly forbidden. |
| **Action Execution** | All actions are non-binding recommendations until accepted and dispatched by an authorized business system. |
| **Customer Contact** | Outreach must strictly honor customer communication preferences, opt-outs, and quiet-hour business policies. |
| **Escalation Protocol** | Cases exhibiting negative sentiment, high financial risk, or explicit customer requests must cleanly transfer to human queues. |
