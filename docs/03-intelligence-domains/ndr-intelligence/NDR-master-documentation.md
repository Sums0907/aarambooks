# NDR Resolution Intelligence Domain (NDR-ID) — Master Architecture & Strategy

**Document Identifier:** `NDR-ID-ARCH-2026-V2`  
**Status:** Canonical Domain Reference & Architectural Baseline  
**Classification:** Foundational Domain Architecture  
**Authoritative Scope:** NDR Resolution Intelligence Domain, Recovery Strategy Engine, Case Lifecycle, and Integration Boundaries.

---

## 1. Executive Summary

The **Non-Delivery Report Resolution Intelligence Domain (NDR-ID)** is an autonomous **Resolution Intelligence and Business Intelligence Application** within the AaramBooks ecosystem.

Its primary purpose is to **determine and support the best possible intervention for each NDR case in order to maximize successful delivery recovery and reduce avoidable Return-to-Origin (RTO).**

NDR-ID moves beyond passive failure logging or simple text analysis. It synthesizes multi-system business context, diagnoses the root causes of delivery exceptions, assesses customer intent and logistical risk, determines targeted recovery strategies, emits governed action recommendations to operational business systems, and continuously learns from downstream physical outcomes.

---

## 2. Business Problem

In modern retail and direct-to-consumer (D2C) commerce, delivery exceptions represent a primary point of margin destruction and customer churn:
1. **Severe Cash Drain (Two-Way Logistics Loss):** Delivery failures that degrade into RTOs force the business to absorb both forward shipping and reverse freight charges with zero revenue realization.
2. **Working Capital & Inventory Lock-in:** Failed shipments trap physical stock in reverse logistics transit loops for 7 to 14 days, causing artificial stockouts of popular items.
3. **Logistics & Doorstep Information Gaps:** Courier failure scans often mask driver skips (fake delivery attempts), temporary customer unavailability, or minor address ambiguities that are completely recoverable if addressed rapidly.
4. **Doorstep Buyer Remorse:** Cash-on-Delivery (COD) orders frequently fail due to doorstep hesitation or payment friction that can be rescued through timely engagement and digital conversion.
5. **Unscalable Manual Operations:** Customer care teams relying on manual spreadsheets and disconnected calling lists cannot intervene within critical operational recovery windows.

---

## 3. Empirical Baseline (Current Business Observation)

> [!NOTE]
> **Observation Baseline:** The figures below represent empirical observations from a sample analysis of **1,189 historical store records** in the operational database. These metrics serve as a business baseline to guide recovery strategy design and are not fixed permanent architectural invariants.

### 3.1 Observed Sample Distribution

| Dimension / Metric | Observed Sample Count | Percentage of Baseline | Strategic Significance |
| :--- | :--- | :--- | :--- |
| **Total Analyzed NDR Cases** | **1,189** | 100% | Full historical observation dataset |
| **Payment Mode: Cash-on-Delivery (COD)** | **1,087** | **91.4%** | Primary cash leak; highest RTO financial exposure |
| **Payment Mode: Prepaid / Online** | **102** | 8.6% | Low RTO risk; focused on delivery convenience |
| **Attempt 1 (Initial Golden Window)** | **666** | **56.0%** | Highest recovery ROI if triaged within 60 minutes |
| **Attempt 2 (Escalating Risk)** | **216** | 18.2% | High urgency re-engagement window |
| **Attempt 3 (Terminal Risk)** | **307** | 25.8% | Final intervention window before irreversible RTO |

### 3.2 Top Observed Failure Modes

| Failure Category | Observed Cases | Share | Observed Underlying Issue | Candidate Strategy Focus |
| :--- | :--- | :--- | :--- | :--- |
| **Customer Unavailable / Unreachable** | 431 | 36.3% | Schedule mismatch, office hours, temporary absence | Autonomous Rescheduling |
| **OTP Rejection / Buyer Remorse** | 333 | 28.0% | Customer hesitation, cash shortage, change of mind | Prepayment Incentive Conversion |
| **Suspected Fake / Skipped Attempt** | 235 | 19.8% | Courier driver skipped doorstep visit | Doorstep Verification & Dispute |
| **Address Incomplete / Missing Landmark** | 101 | 8.4% | Landmark missing, incorrect building number | Landmark & Location Enrichment |
| **Delivery Rescheduled by Customer** | 89 | 7.5% | Direct customer request for later date | Automated Date Commitment |

---

## 4. Business Value Model

NDR-ID creates measurable economic value across four core pillars:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              NDR-ID BUSINESS VALUE MODEL                                │
│                                                                                         │
│  [ Delivery Failure Exception ] ──► [ NDR-ID Resolution Intelligence ]                  │
│                                                │                                        │
│         ┌───────────────────────────┬──────────┴────────────────┬────────────────────┐  │
│         ▼                           ▼                           ▼                    ▼  │
│  Deliveries Recovered       Avoidable RTO Reduction      Revenue Protected   Operational Velocity│
│  (Rescheduled & Completed)  (Reverse Freight Eliminated) (Preserved Margins) (Targeted Human Focus)│
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Deliveries Recovered:** Converting delivery exceptions into verified doorstep handoffs.
2. **RTO & Freight Cost Avoidance:** Eliminating unnecessary reverse shipping fees, warehouse re-processing costs, and transit packaging damage.
3. **Revenue Protection:** Rescuing orders and converting COD hesitation to guaranteed prepaid revenue.
4. **Operational Efficiency:** Automating high-volume routine triage so human customer care specialists focus exclusively on complex exceptions.

---

## 5. NDR-ID Role: Resolution Intelligence Application

NDR-ID is a **Business Intelligence Application**, not an operational logistics management system.

- It **observes** delivery failure signals from business truth systems.
- It **understands** the multi-factor context surrounding the customer, order, and courier.
- It **diagnoses** the root cause of the delivery exception.
- It **formulates** optimal recovery strategies and coordinates customer communication.
- It **recommends** precise operational actions to authoritative business systems.
- It **measures** whether those actions resulted in successful physical delivery.
- It **learns** from every outcome to continuously refine future intelligence.

---

## 6. Architecture Boundary & Ownership

NDR-ID strictly enforces the foundational AaramBooks ownership philosophy:

> **Business systems create truth.**  
> **Aaram Brain creates intelligence from that truth.**  
> **Intelligence Domains apply that intelligence to business objectives.**

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: BUSINESS TRUTH (Operational Systems of Record)                       │
│    • Own order truth, customer truth, shipment truth, and delivery truth.     │
│    • Retain exclusive authority to execute logistics and financial actions.   │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Publishes trusted records & read views
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: SHARED INTELLIGENCE FOUNDATION (Aaram Brain Core & Global Azm)       │
│    • Provides generic reasoning, context planning, decision, and memory.      │
│    • Completely domain-agnostic; zero hardcoded NDR business logic.           │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Powers domain specialist capabilities
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: INTELLIGENCE APPLICATIONS (NDR Resolution Intelligence / NDR-ID)     │
│    • Owns NDR-specific failure diagnosis, risk assessment, & recovery strategy.│
│    • Formulates recommended interventions; NEVER directly mutates truth.     │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ Emits governed action proposals
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: OPERATIONAL EXECUTION & OUTCOME BOUNDARY                             │
│    • Business systems execute reattempts, update records, or file disputes.   │
│    • Physical delivery outcomes flow back into Layer 1 as new truth.          │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Strict Boundary Invariants:
- **NDR-ID does NOT own master data:** Customer profiles, orders, inventory, and shipment states are owned exclusively by business systems.
- **NDR-ID does NOT execute operational changes directly:** It formulates governed action recommendations; the responsible business domain retains execution authority.
- **NDR-ID does NOT duplicate databases:** It operates on federated read projections.

---

## 7. Relationship With Aaram Brain Core

NDR-ID sits in Layer 3 (Intelligence Applications), consuming shared services from Layer 2 (Brain Core & Global Azm):

| Brain Core / Azm Subsystem | How NDR-ID Leverages It |
| :--- | :--- |
| **Context Engine** | Dynamically federates multi-system context (shipment, customer, order, attempts). |
| **Knowledge Engine (Global Azm)** | Resolves namespaced NDR concepts, reason codes, SLA policies, and public read contracts. |
| **Reasoning Engine** | Interprets ambiguous customer messages, courier notes, and situational discrepancies. |
| **Decision Engine** | Evaluates candidate strategies against business policies, risk thresholds, and confidence limits. |
| **Action Engine** | Formulates governed, typed action requests for business system execution. |
| **Memory Framework** | Persists resolution case history and outcome evaluation loops for continuous learning. |
| **Model Gateway** | Provides model-agnostic LLM access for intent parsing and conversational generation. |

---

## 8. The Canonical NDR Intelligence Lifecycle

Every delivery exception processed by NDR-ID moves through structured conceptual stages:

```
1. NDR Signal Ingestion
   │ (Delivery failure exception published by logistics source)
   ▼
2. Situation Understanding
   │ (Initial parsing of courier code, failure category, and event timestamp)
   ▼
3. Relevant Context Assembly
   │ (Federate order financials, customer history, delivery attempts, & carrier profile)
   ▼
4. Failure Diagnosis
   │ (Identify root cause: unreachable, address gap, fake attempt, buyer remorse)
   ▼
5. Customer Intent & State Assessment
   │ (Evaluate customer responsiveness, past interactions, & current sentiment)
   ▼
6. Priority & Risk Assessment
   │ (Synthesize operational risk, commercial priority, and customer experience risk)
   ▼
7. Recovery Strategy Determination
   │ (Select optimal candidate strategy pattern based on context, policy, & confidence)
   ▼
8. Recommendation Generation
   │ (Formulate governed, typed action proposal with confidence & justification)
   ▼
9. Customer / Human Interaction (Where Required)
   │ (Interactive multi-channel outreach or human support escalation handoff)
   ▼
10. Business-System Execution
   │ (Authoritative business system commits reattempt, updates address, or files claim)
   ▼
11. Outcome Observation
   │ (Monitor downstream tracking events: Delivered, Reattempted, RTO, Cancelled)
   ▼
12. Outcome Evaluation
   │ (Compare actual operational outcome against strategy prediction)
   ▼
13. Continuous Learning
   │ (Update strategy confidence, courier reliability patterns, & domain heuristics)
```

---

## 9. Decision Intelligence Framework

NDR-ID synthesizes multiple contextual dimensions to formulate an optimal resolution recommendation:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          NDR-ID MULTI-FACTOR SYNTHESIS                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Failure Exception Context    • Delivery Attempt History    • Shipment & Item Data    │
│ • Financial & Order Value      • Customer Lifetime Profile   • Customer Intent & State │
│ • Interaction History          • Courier Reliability Index   • Business Policies & SOPs│
│ • Historical Outcome Matches   • RTO Risk & Recovery Likelihood • Model Confidence     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Decision Output Categories:
1. **Recovery Strategy Selection:** Identifying the highest-probability recovery approach.
2. **Priority Assessment:** Ranking operational urgency based on value and time sensitivity.
3. **Risk Identification:** Pinpointing severe RTO exposure or courier service anomalies.
4. **Escalation Suggestion:** Recommending human intervention when automated rules are insufficient.
5. **Action Parameterization:** Supplying precise operational parameters (dates, landmarks, incentives).

---

## 10. Recovery Strategy Framework

A failure reason code does **not** equal a fixed action. NDR-ID treats **Recovery Strategy** as a dynamic cognitive synthesis between failure diagnosis, customer state, risk, policy, and past outcome patterns.

### Candidate Strategy Patterns (Illustrative Archetypes):

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

---

## 11. Priority & Risk Intelligence

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

## 12. Customer Interaction Intelligence

NDR-ID orchestrates customer communication to clarify intent and collect recovery parameters:
- **Intelligent Channel Sequencing:** Selects optimal communication channels based on urgency and time elapsed (e.g. interactive messaging followed by smart voice fallback).
- **Conversational Thread Continuity:** Maintains seamless context across multi-turn exchanges and channel transitions.
- **Low-Friction Inputs:** Prioritizes structured, one-tap actions (interactive buttons, quick date selectors) over open-ended text entry.

---

## 13. Human Escalation Intelligence

Escalation is an active, intelligence-driven recommendation rather than a simple system failure:

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENT ESCALATION TRIGGERS                           │
├───────────────────────────────────────────────────────────────────────────────┤
│ • Explicit Customer Request: Customer asks for human support.                 │
│ • Low Model Confidence: Ambiguous customer intent or conflicting context.     │
│ • High Commercial Value: High-ticket order exceeding autonomous limits.       │
│ • Policy Boundary Exception: Customer request outside standard business SOPs. │
│ • Severe Negative Sentiment: High customer frustration or dispute.            │
│ • Repeated Intervention Failure: Case has failed prior automated recovery.    │
│ • Operational Logistics Anomaly: Irregular transit or carrier scan patterns.  │
└───────────────────────────────────────────────────────────────────────────────┘
```

When escalating, NDR-ID compiles a structured briefing dossier for human support agents.

---

## 14. Outcome Intelligence

NDR-ID maintains a strict distinction across the outcome verification chain:

$$\text{Recommendation Accepted} \neq \text{Action Executed} \neq \text{Customer Engaged} \neq \text{Delivery Recovered} \neq \text{RTO Avoided}$$

```
[ NDR-ID Recommendation Emitted ]
               │
               ▼
[ Business System Execution ] ──── Distinct Event: Was the action technically applied?
               │
               ▼
[ Customer Engagement ] ────────── Distinct Event: Did the customer respond?
               │
               ▼
[ Physical Logistics Reattempt ] ─ Distinct Event: Did the courier reattempt delivery?
               │
               ▼
[ Final Physical Delivery ] ────── Final Truth: DELIVERED vs RETURNED TO ORIGIN (RTO)
```

> [!IMPORTANT]
> **Key Principle:** A recommendation being accepted is not the same as a successful delivery. A successful customer interaction is not the same as a successful delivery recovery. Only verified physical handoff constitutes recovery.

---

## 15. The Continuous Learning Loop

Physical outcomes are fed back into domain memory to refine intelligence:
- **Strategy Effectiveness:** Tracking recovery yield per strategy pattern across failure modes.
- **Carrier Performance:** Updating courier and hub reliability ratings.
- **Geographic Insights:** Identifying pincodes with chronic delivery issues.
- **Timing Optimization:** Refining outreach latency windows for maximum customer responsiveness.

---

## 16. Conceptual NDR Intelligence Model

The conceptual information model of an NDR Case encompasses:
- **Case Identifier & State:** Unique case identity and current lifecycle state.
- **Shipment Identification & Logistics Metadata:** Tracking number, carrier, origin, destination.
- **Customer Context:** Customer profile, past purchase/RTO history, contact references.
- **Order Financials:** Order value, payment mode, product items.
- **Delivery Attempt History:** Attempt numbers, timestamps, recorded carrier notes.
- **Outreach & Interaction Timeline:** History of communications, customer replies, sentiment.
- **Diagnostic Synthesis:** Classified failure mode, root-cause interpretation.
- **Risk & Priority Scores:** Computed RTO risk, commercial priority index, recovery probability.
- **Active Recovery Strategy:** Selected strategy archetype, parameters, and rationale.
- **Outcome Records:** Technical execution status, customer response status, and final physical delivery result.

---

## 17. Integration Boundaries

```
[ Customer Channels (WhatsApp/IVR) ] ◄──► [ NDR-ID ] ◄──► [ Business Systems (ShopDeck) ]
                                            │                      │
                                            ▼                      ▼
                                   [ Aaram Brain Core ]    [ Courier & Logistics ]
```

- **Business Truth Systems:** Provide read projections; receive structured action proposals.
- **Logistics Systems:** Supply raw exception signals; receive reattempt instructions via business systems.
- **Customer Channels:** Execute conversational prompts; return customer intent.
- **Human Support:** Receives escalation dossiers; supplies manual resolution feedback.
- **Brain Core:** Supplies domain-agnostic reasoning, planning, memory, and model gateway services.

---

## 18. Architectural Governance & Safety Guardrails

1. **Read-Only Data Access:** NDR-ID accesses business truth exclusively through published read contracts.
2. **Governed Action Proposals:** All outputs are non-binding recommendations until committed by business systems.
3. **Policy Boundary Compliance:** Autonomous incentive and rescheduling offers must strictly honor policy rules in Azm.
4. **Privacy & Communication Discipline:** All customer outreach adheres to quiet hours, frequency caps, and opt-out policies.

---

## 19. Success Metrics Hierarchy

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SUCCESS METRICS HIERARCHY                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🏆 TIER 1: BUSINESS VALUE OUTCOMES (The Ultimate Measure)                              │
│    • Deliveries Recovered (Count & %)  • Avoidable RTO Rate Reduction                  │
│    • Net Revenue Protected             • Two-Way Logistics Cost Avoided                │
│    • Successful Reattempt Rate         • Net Margin Preservation                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 👥 TIER 2: CUSTOMER & OPERATIONAL OUTCOMES (Experience & Team Impact)                  │
│    • Resolution Success Rate           • Customer Engagement & Response Velocity       │
│    • Post-Intervention Sentiment       • Support Workload Optimization                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🧠 TIER 3: INTELLIGENCE QUALITY (Supporting Foundation)                                │
│    • Recommendation Acceptance Rate    • Intent Extraction Precision                   │
│    • Priority & Risk Calibration       • Human Override Rate                           │
│    • Escalation Precision & Recall     • Strategy Learning Drift                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 20. Recorded Architectural Decisions

- **ADR-NDR-001 (Business Intelligence Role):** NDR-ID is designated as a Resolution Intelligence Application, not an operational execution system.
- **ADR-NDR-002 (Strategy Decoupling):** Recovery Strategy is established as an explicit cognitive stage between failure diagnosis and action recommendation.
- **ADR-NDR-003 (Closed-Loop Outcome Separation):** Operational execution, customer communication, and physical delivery recovery are modeled as separate, distinct outcome tiers.
- **ADR-NDR-004 (Empirical Baseline Grounding):** Historical store records (1,189 cases) are treated as empirical observations rather than rigid architectural rules.

---

## 21. Open Decisions

### A. Architectural Decisions
1. **Dynamic Strategy Policy Registration in Azm:** Standardizing the declarative schema for expressing recovery strategy constraints and eligibility rules within the Azm semantic knowledge layer.

### B. Business Policy Decisions
1. **Autonomous Financial Incentive Delegation:** Defining the exact discount percentage limits, gift voucher caps, and margin thresholds under which NDR-ID may autonomously offer prepayment incentives without human sign-off.
2. **Multi-Recipient Outreach Policy:** Establishing business rules and consent boundaries for reaching out to alternate contacts or family members when the primary buyer is unreachable.

### C. Operational & Integration Decisions
1. **Carrier Dispute Ingestion Gateway:** Determining whether carrier dispute escalations should be dispatched through the merchant aggregator gateway (e.g. ShopDeck / Shiprocket) or directly into 3PL carrier claims APIs.

---

## 22. NDR-ID Business Value Expectations

NDR-ID is architected to deliver substantial, measurable improvements against unassisted baselines:
- **Measurable RTO Rate Reduction:** Driving down avoidable delivery failures across COD and prepaid shipments.
- **Working Capital Velocity:** Minimizing inventory trapped in transit loops.
- **Preserved Customer Trust:** Replacing silent cancellations with proactive, supportive delivery resolutions.
- **Continuous Intelligence Optimization:** Growing smarter and more effective with every observed delivery outcome.
