# NDR Resolution Intelligence Technical Design Architecture

## 1. Domain Purpose & Technical Scope

The **NDR Resolution Intelligence Domain (NDR-ID)** is the specialized business intelligence domain responsible for diagnosing delivery exceptions, formulating optimal recovery strategies, coordinating customer intent discovery, and producing governed intervention recommendations to minimize Return-to-Origin (RTO) losses.

### Technical Scope:
- **In Scope:** Cognitive failure diagnosis, multi-factor contextual synthesis, priority and risk scoring, candidate strategy selection, conversational interaction management, escalation routing, outcome evaluation, and continuous strategy learning.
- **Out of Scope:** Physical logistics execution, courier routing management, customer master data ownership, financial order processing, direct database table mutation, telephony hardware protocols, and messaging transport infrastructure.

---

## 2. Technical Architecture & Conceptual Capabilities

NDR-ID is organized around core conceptual intelligence capabilities:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   NDR RESOLUTION INTELLIGENCE DOMAIN (NDR-ID)                          │
│                                                                                        │
│  ┌──────────────────────────────┐        ┌──────────────────────────────┐              │
│  │ Case Management Capability   │        │ Context Assembly Capability  │              │
│  │ (Lifecycle & State Tracking) │        │ (Multi-System Federation)    │              │
│  └──────────────┬───────────────┘        └──────────────┬───────────────┘              │
│                 │                                       │                              │
│                 ▼                                       ▼                              │
│  ┌──────────────────────────────┐        ┌──────────────────────────────┐              │
│  │ Failure Diagnosis Capability │        │ Priority & Risk Capability   │              │
│  │ (Semantic Root-Cause Parser) │        │ (Commercial & RTO Scoring)   │              │
│  └──────────────┬───────────────┘        └──────────────┬───────────────┘              │
│                 │                                       │                              │
│                 └───────────────────┬───────────────────┘                              │
│                                     ▼                                                  │
│                          ┌──────────────────────┐                                      │
│                          │ Recovery Strategy    │                                      │
│                          │ Reasoning Capability │                                      │
│                          └──────────┬───────────┘                                      │
│                                     │                                                  │
│                 ┌───────────────────┴───────────────────┐                              │
│                 ▼                                       ▼                              │
│  ┌──────────────────────────────┐        ┌──────────────────────────────┐              │
│  │ Interaction Intelligence     │        │ Escalation Intelligence      │              │
│  │ (Multi-Channel Dialogue)     │        │ (Risk, Ambiguity, Concierge) │              │
│  └──────────────┬───────────────┘        └──────────────┬───────────────┘              │
│                 │                                       │                              │
│                 └───────────────────┬───────────────────┘                              │
│                                     ▼                                                  │
│                          ┌──────────────────────┐                                      │
│                          │ Outcome & Learning   │                                      │
│                          │ Closed-Loop Engine   │                                      │
│                          └──────────────────────┘                                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Intelligence Capabilities

### 3.1 NDR Case Lifecycle Management
- **Role:** Tracks the formal lifecycle of an active resolution journey from initial failure signal to final outcome evaluation.
- **State Model:**
  - `CaseCreated`: Initial failure signal captured.
  - `ContextAssembled`: Context federated across business systems.
  - `FailureDiagnosed`: Semantic failure category identified.
  - `StrategyFormulated`: Candidate strategy selected and parameterized.
  - `InteractionActive`: Outreach dispatched to customer.
  - `IntentResolved`: Customer preferences or commitments confirmed.
  - `RecommendationReady`: Structured action proposal emitted.
  - `ExecutionPending` / `ExecutionAcknowledged`: Dispatched to and acknowledged by business systems.
  - `OutcomeObserved`: Physical tracking outcome ingested.
  - `OutcomeEvaluated`: Success or failure measured against strategy expectation.
  - `EscalatedToHuman`: Case routed to manual concierge support.
  - `CaseClosed`: Lifecycle completed; learning evidence committed to memory.

### 3.2 Context Assembly Capability
- **Role:** Synthesizes a unified, multi-dimensional conceptual context container without hardcoding database schemas or tight couplings:
  - *Shipment Context:* AWB reference, carrier name, tracking events, dispatch origin, destination pincode, transit days.
  - *Customer Context:* Contact details, past order frequency, past RTO history, communication preferences.
  - *Order Financial Context:* Order commercial value, item descriptions, payment mode (COD vs Prepaid), gross margin.
  - *Delivery Attempt History:* Cumulative attempt count, out-for-delivery timestamps, recorded carrier notes.
  - *Interaction History:* Chronological log of previous outreach attempts, responses, and customer sentiment.
  - *Courier Profile Context:* Historical reliability, dispute frequency, and delivery success rates for the assigned hub.

### 3.3 Failure Diagnosis Capability
- **Role:** Translates raw, disparate courier exception codes into canonical, business-understandable failure modes:
  - *Unavailability:* Customer not reachable, door locked, out of station.
  - *Address Issue:* Incomplete street address, missing landmark, incorrect pincode, unserviceable area.
  - *Buyer Hesitation / Rejection:* OTP refusal, cash shortage, cancelled at doorstep, product remorse.
  - *Suspected Courier Defect:* Driver skip, marked failed without doorstep visit, premature RTO scan.
  - *Operational Delay:* Delivery vehicle breakdown, weather disruption, entry gate access restriction.

### 3.4 Priority & Risk Intelligence Capability
- **Role:** Evaluates operational urgency and recovery likelihood across three distinct dimensions:
  - *Operational Risk:* Attempt degradation, payment mode exposure, carrier hub fake-attempt rate, transit latency.
  - *Commercial Priority:* Total order commercial value, gross contribution margin, inventory stockout criticality.
  - *Customer Experience Risk:* Customer lifetime value (LTV), repeat buyer tier, sentiment distress.

### 3.5 Recovery Strategy Reasoning Capability
- **Role:** Evaluates multi-factor context against candidate strategy patterns and organizational policies:
  - Dynamically matches diagnosed failure modes, risk levels, and customer states to candidate playbooks (e.g. Autonomous Reschedule, Doorstep Verification/Dispute, Prepayment Incentive Conversion, Landmark Enrichment).
  - Formulates structured, parameter-complete action recommendations.

### 3.6 Customer Interaction Intelligence Capability
- **Role:** Orchestrates the conversational engagement flow with the recipient:
  - Manages channel sequencing (e.g., immediate interactive messaging with timed voice call fallback).
  - Translates unstructured natural language or button inputs into verified structured commitments.
  - Maintains conversation context continuity across multi-turn exchanges.

### 3.7 Human Escalation Intelligence Capability
- **Role:** Identifies cases where automated resolution is unsafe, ambiguous, or high-risk:
  - Evaluates escalation triggers: explicit customer demand, low model confidence, high commercial stakes, policy boundary breaches, severe frustration sentiment, or repeated automated failures.
  - Assembles a structured briefing dossier for customer care agents.

### 3.8 Outcome Intelligence & Learning Capability
- **Role:** Closes the feedback loop by evaluating physical operational outcomes against strategy predictions:
  - Distinguishes technical execution, customer response, and final delivery recovery.
  - Updates strategy confidence priors, carrier reliability indexes, and domain heuristics in Aaram Brain memory without mutating operational records.

---

## 4. Relationship With Aaram Brain Core

NDR-ID strictly delegates generic, shared cognitive tasks to **Aaram Brain Core**:

```
┌────────────────────────────────────────┐
│     NDR RESOLUTION INTELLIGENCE        │
│   (Domain-Specific Business Logic)     │
│                                        │
│ • NDR Case Lifecycle State Machine     │
│ • Delivery Recovery Strategy Patterns  │
│ • Delivery Failure Diagnostic Heuristics│
│ • Courier Dispute Reasoning            │
└───────────────────┬────────────────────┘
                    │ Consumes Generic Platforms
                    ▼
┌────────────────────────────────────────┐
│           AARAM BRAIN CORE             │
│    (Domain-Agnostic AI Machinery)      │
│                                        │
│ • Context Engine & Provider Registry   │
│ • Knowledge Engine (Global Azm)        │
│ • Reasoning & Decision Engines         │
│ • Memory Framework & Learning Store    │
│ • Model Gateway (LiteLLM / Qwen / API) │
└────────────────────────────────────────┘
```

---

## 5. Architectural Governance & Invariants

1. **Zero Operational Truth Ownership:** NDR-ID does not own or mutate order statuses, shipment records, or financial balances.
2. **Recommendation-Only Output:** NDR-ID outputs non-binding, structured action proposals. Operational systems retain ultimate execution authority.
3. **Strict Abstraction:** No database table schemas, SQL joins, HTTP endpoints, or vendor-specific communication APIs are hardcoded within NDR-ID architecture.
4. **Safety & Policy Guardrails:** Autonomous outreach and incentive offers must strictly adhere to certified business policies registered in Azm.
