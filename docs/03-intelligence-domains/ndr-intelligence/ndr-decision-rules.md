# NDR Decision Intelligence Framework & Strategy Selection

## 1. Purpose & Decision Principles

This document defines the formal **Decision Intelligence Framework** of the **NDR Resolution Intelligence Domain (NDR-ID)**.

### Foundational Principles:
1. **Multi-Factor Synthesis:** A failure reason code alone must never deterministically dictate a resolution action. Real-world delivery recovery requires synthesizing failure context, attempt history, customer sentiment, business value, and logistical constraints.
2. **Recovery Strategy as a First-Class Concept:** NDR-ID formulates a high-level *Recovery Strategy* before generating granular intervention recommendations.
3. **Separation of Risk, Priority, and Experience:** Operational Risk, Commercial Priority, and Customer Experience Risk are evaluated as distinct dimensions.
4. **Policy Supremacy:** Commercial priority or customer VIP status never grants authority to violate certified business policies or alter operational truth. Priority guides attention allocation and concierge routing.
5. **Intelligence vs. Execution Boundary:** NDR-ID produces reasoned recommendations accompanied by confidence scores and business justifications. Operational business systems retain sole authority to approve, execute, or override those recommendations.

---

## 2. Multi-Factor Context Synthesis

NDR-ID synthesizes multiple contextual dimensions to formulate an accurate diagnosis and recovery plan:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          NDR-ID MULTI-FACTOR CONTEXT SYNTHESIS                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Failure Exception Facts  ──► [ Courier code, exception description, event timestamp ] │
│ • Delivery Attempt History ──► [ Attempt count, OFD count, elapsed days in transit ]   │
│ • Shipment & Package Data  ──► [ Weight, dimensions, fragility, category, SKU profile ]│
│ • Order & Financial Value  ──► [ Total order value, COD amount, gross margin profile ] │
│ • Customer Profile Context ──► [ Purchase frequency, past RTO history, VIP tier ]      │
│ • Customer Intent & State  ──► [ Inbound message, response velocity, sentiment tone ]  │
│ • Past Interaction History ──► [ Previous calls, messaging status, customer feedback ] │
│ • Courier Reliability Data ──► [ Hub fake-attempt frequency, carrier SLA score ]       │
│ • Business Policies & SOPs ──► [ Max allowed retries, incentive caps, quiet hours ]   │
│ • Historical Outcome Data  ──► [ Prior recovery rates for matching contextual patterns]│
│ • Recovery Probability     ──► [ Estimated statistical likelihood of delivery success ]│
│ • Model Confidence Level   ──► [ Certainty score of the reasoning synthesis ]          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Recovery Strategy as a First-Class Concept

The core architectural flaw of naive delivery exception handling is treating failure codes as rigid, hardcoded routing triggers. NDR-ID introduces **Recovery Strategy** as an intermediate, flexible cognitive abstraction:

```
    [ Failure Code & Signal ]
               │
               ▼
    [ Situation & Context Understanding ]
               │
               ▼
    [ Multi-Factor Synthesis ]
      (Operational Risk + Commercial Priority + Customer State + Policy + History)
               │
               ▼
    [ Recovery Strategy Formulation ] ◄── (Matches optimal candidate strategy pattern)
               │
               ▼
    [ Structured Action Recommendation ]
```

### Strategy Formulation Flow:
- **Step 1: Situation Disambiguation:** Differentiating between a genuine customer scheduling conflict, an address defect, a financial hesitation (COD cash shortage), or a courier failure (driver skip / false scan).
- **Step 2: Candidate Strategy Selection:** Evaluating candidate strategy patterns against business constraints and past recovery likelihood.
- **Step 3: Intervention Parameterization:** Customizing the strategy with concrete parameters (e.g. selected reattempt date, landmark addition, discount incentive, or carrier dispute evidence).

---

## 4. Candidate Recovery Strategy Patterns

NDR-ID maintains a library of candidate strategy patterns that represent proven operational archetypes for delivery rescue:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CANDIDATE RECOVERY STRATEGY PATTERNS                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Autonomous Rescheduling Strategy                                                    │
│    • Context: Customer temporarily unavailable or requested a future delivery date.    │
│    • Objective: Capture a firm commitment date and inject it into carrier schedule.   │
│    • Interaction: Single-tap date selection via interactive communication.            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Doorstep Verification & Carrier Dispute Strategy                                    │
│    • Context: Suspected fake delivery attempt (driver marked failed without doorstep).  │
│    • Objective: Verify customer reality, collect evidence, & force carrier reattempt. │
│    • Interaction: Two-way verification check ("Did the courier arrive at your home?").│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Buyer Commitment & Payment Conversion Strategy                                      │
│    • Context: COD order exhibiting hesitation, price remorse, or OTP reluctance.       │
│    • Objective: Secure prepayment or reaffirm purchase intent before reattempt.        │
│    • Interaction: Offer approved prepayment incentives or instant digital payment.    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Address Enrichment & Geolocation Capture Strategy                                   │
│    • Context: Courier reported incomplete address, missing landmark, or wrong pincode.│
│    • Objective: Gather specific landmark, alternate contact, or map pin.              │
│    • Interaction: Conversational landmark prompt or location sharing request.          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. Priority Concierge Escalation Strategy                                              │
│    • Context: High-value order, severe customer distress, or repeated failure cycles. │
│    • Objective: Transfer full case context to a specialized human support agent.       │
│    • Interaction: Direct concierge voice outreach and manual carrier coordination.     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

> [!NOTE]
> **Architectural Clarification:** These playbooks are **candidate strategy patterns**, not hardcoded routing tables. The decision engine dynamically selects, combines, or adapts these strategies based on multi-factor context.

---

## 5. Priority, Risk, and Experience Intelligence

NDR-ID explicitly separates three distinct analytical dimensions:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      DISTINCT RISK & PRIORITY DIMENSIONS                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ⚠️ OPERATIONAL RISK                                                                    │
│ • Measures the physical probability of delivery failure.                               │
│ • Factors: Attempt count, payment mode (COD vs Prepaid), carrier hub fake-attempt rate,│
│   elapsed days in transit, customer response latency.                                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 💰 COMMERCIAL PRIORITY                                                                 │
│ • Measures the financial impact of the order to the business.                          │
│ • Factors: Total order commercial value, gross contribution margin, inventory scarcity.│
│ • Invariant: High commercial value prioritizes attention; it NEVER bypasses policy.    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🌟 CUSTOMER EXPERIENCE RISK                                                            │
│ • Measures the relationship and brand impact of the interaction.                       │
│ • Factors: Customer lifetime value (LTV), repeat buyer tier, sentiment distress,       │
│   prior unresolved complaints or disputes.                                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Human Escalation Intelligence

Human escalation in NDR-ID is an intelligent triage decision rather than a simple error fallback:

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENT ESCALATION TRIGGERS                           │
├───────────────────────────────────────────────────────────────────────────────┤
│ • Explicit Customer Request: Customer requests to speak with an agent.        │
│ • Low Model Confidence: Customer reply is ambiguous or contradicts context.   │
│ • High Commercial Stakes: Order value exceeds standard autonomous thresholds. │
│ • Policy Boundary Exception: Customer requests an action outside standard rules│
│ • Negative Sentiment / Dispute: Customer expresses high frustration or anger. │
│ • Repeated Intervention Failure: Case has failed previous automated triage.   │
│ • Operational Anomaly: Courier behavior exhibits irregular transit patterns.  │
└───────────────────────────────────────────────────────────────────────────────┘
```

When escalation occurs, NDR-ID compiles a structured briefing dossier (chronological history, sentiment analysis, diagnosed failure root cause, and suggested talking points) for human support agents.

---

## 7. Decision Intelligence vs. Execution Authority

NDR-ID enforces strict boundary separation between cognitive recommendation and operational execution:

| Stage | Responsibility of NDR-ID | Responsibility of Business System |
| :--- | :--- | :--- |
| **Analysis & Diagnosis** | Synthesizes multi-factor context and diagnoses root cause. | Provides read views and authoritative records. |
| **Strategy Formulation** | Evaluates candidate strategies and predicts recovery likelihood. | Enforces business policy guardrails and authorization. |
| **Recommendation** | Emits typed, structured action proposal with justification. | Receives, reviews, and logs the action recommendation. |
| **Execution** | *None (Zero execution authority).* | Commits changes to carrier APIs, updates order notes, or updates payment state. |
| **Outcome Tracking** | Evaluates whether physical delivery succeeded. | Records downstream delivery and logistics events. |
