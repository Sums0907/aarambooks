# NDR Intelligence Technical Design Specification

## 1. NDR Intelligence Purpose

The Non-Delivery Report (NDR) Intelligence Domain exists to orchestrate and optimize the resolution of failed delivery attempts within the AaramBooks ecosystem.

**Business Problem:** Delivery failures result in high return-to-origin (RTO) costs, delayed revenue, and poor customer experiences. Manual handling of these exceptions is slow and unscalable.
**Why This Domain Exists:** To provide a specialized intelligence application that systematically resolves NDRs using AI-driven context and conversation, separate from the generic Brain Core.
**Expected Business Outcomes:**
- Reducing delivery failures and RTO rates.
- Improving proactive customer communication regarding delivery issues.
- Increasing successful delivery outcomes through timely, intelligent interventions.
- Reducing manual NDR handling efforts by customer support teams.

---

## 2. NDR Intelligence Boundary

NDR Intelligence operates as an independent Intelligence Domain within the AaramBooks ecosystem.

**Owns:**
- NDR intelligence workflow and orchestration.
- Resolution intelligence (determining the best path to fix an NDR).
- Customer communication intelligence (managing the NDR conversation).
- Escalation intelligence (knowing when a human is required).
- Outcome analysis (evaluating the success of interventions).

**Does NOT own:**
- Customer master data.
- Order truth.
- Shipment truth.
- Inventory truth.
- Logistics execution.
- Operational status databases.

---

## 3. Relationship With Aaram Brain Core

NDR Intelligence leverages the generic capabilities of Aaram Brain Core without embedding NDR-specific workflows inside the core.

- **Context Engine:** Provides shipment context, customer context, and previous interaction context.
- **Knowledge Engine:** Provides organizational policies, SOPs, and resolution guidelines for failed deliveries.
- **Reasoning Engine:** Provides failure analysis (interpreting why the delivery failed), intent understanding (what the customer wants), and situation analysis.
- **Decision Engine:** Provides resolution recommendations and escalation recommendations based on reasoning outputs.
- **Action Engine:** Provides controlled execution requests formatted for the appropriate Business Domain Systems.

---

## 4. NDR Intelligence Internal Architecture

The NDR Intelligence domain consists of several specific orchestration components:

- **NDR Case Management:** 
  - *Responsibility:* Tracks the active lifecycle of an NDR resolution attempt.
  - *Inputs:* Inbound NDR events.
  - *Outputs:* Case state updates.
  - *Dependencies:* Context Engine.
- **Resolution Intelligence:** 
  - *Responsibility:* Determines the strategy for fixing the NDR.
  - *Inputs:* Failure reasons, Context.
  - *Outputs:* Resolution plans.
  - *Dependencies:* Reasoning Engine, Decision Engine.
- **Customer Communication Intelligence:** 
  - *Responsibility:* Manages the conversational flow with the customer.
  - *Inputs:* Customer replies, Context.
  - *Outputs:* Conversational prompts, intent triggers.
  - *Dependencies:* Reasoning Engine.
- **Escalation Intelligence:** 
  - *Responsibility:* Monitors risk and decides if human intervention is required.
  - *Inputs:* Conversation sentiment, failure thresholds.
  - *Outputs:* Escalation alerts.
  - *Dependencies:* Decision Engine.
- **Outcome Intelligence:** 
  - *Responsibility:* Tracks and analyzes the success of the applied resolution.
  - *Inputs:* Post-resolution logistics events.
  - *Outputs:* Learning feedback.
  - *Dependencies:* Memory Framework.

---

## 5. NDR Intelligence Lifecycle

The complete lifecycle of resolving an NDR flows as follows:

1. **NDR Event Received:** An inbound event indicates a delivery failure.
2. **NDR Case Created:** The domain initializes an orchestration case.
3. **Context Assembly:** Calls the Context Engine to gather order, customer, and shipment details.
4. **Failure Reason Understanding:** Calls the Reasoning Engine to interpret the courier's failure code.
5. **Customer Interaction:** Reaches out to the customer via the appropriate channel.
6. **Intent Understanding:** Calls the Reasoning Engine to analyze the customer's response (e.g., "I moved" or "I want a refund").
7. **Resolution Decision:** Calls the Decision Engine to determine the best outcome (e.g., update address, schedule retry).
8. **Action Request:** Calls the Action Engine to formulate an execution request for the Business Domain.
9. **Outcome Tracking:** Monitors subsequent events to see if the resolution succeeded.
10. **Learning Feedback:** Sends success/failure patterns to Brain Core's Memory Framework to improve future reasoning.

---

## 6. Context Requirements

NDR Intelligence requires the fusion of two distinct types of context:

**Operational Context (Provided by Business Systems):**
- Order details (items, value, status).
- Shipment details (tracking ID, carrier).
- Delivery attempts (timestamps, courier codes).
- Logistics information (current node, constraints).

**Intelligence Context (Provided by Brain Core):**
- Previous conversations (did the customer already complain about this?).
- Customer interaction history (is this a VIP or high-risk customer?).
- Learned patterns (does this courier often fake delivery attempts in this area?).
- Resolution history (what worked last time?).

---

## 7. Customer Conversation Intelligence

NDR Intelligence orchestrates interactions with the customer to resolve the failure.
- **Customer interaction handling:** Manages the timing, channel, and tone of outreach.
- **Intent understanding:** Translates raw customer text/voice into structured business intents (e.g., `Address Update`, `Reschedule`, `Cancel`).
- **Conversation continuity:** Maintains the thread of conversation across multiple messages or channels.
- **Escalation triggers:** Automatically routes the conversation to a human agent if the customer is frustrated, the intent is ambiguous, or the value is high.
*(Note: Voice/STT/TTS implementation details are excluded from this specification.)*

---

## 8. Resolution Decision Framework

When the customer's intent is understood, the domain determines the appropriate outcome:

- **Retry Delivery:**
  - *Required Context:* Original address, courier constraints.
  - *Decision Responsibility:* NDR Intelligence.
  - *Execution Authority:* Logistics Domain System.
- **Schedule Delivery:**
  - *Required Context:* Customer preferred time, courier SLA.
  - *Decision Responsibility:* NDR Intelligence.
  - *Execution Authority:* Logistics Domain System.
- **Address Verification/Correction:**
  - *Required Context:* New address input, validation rules.
  - *Decision Responsibility:* NDR Intelligence.
  - *Execution Authority:* ShopDeck / Logistics Domain System.
- **Customer Clarification:**
  - *Required Context:* Ambiguous response.
  - *Decision Responsibility:* NDR Intelligence.
  - *Execution Authority:* Customer Communication Channel.
- **Escalate to Human:**
  - *Required Context:* Escalation policies, agent availability.
  - *Decision Responsibility:* NDR Intelligence.
  - *Execution Authority:* Support Ticketing System.
- **Cancel/Refund Request:**
  - *Required Context:* Order value, return policies.
  - *Decision Responsibility:* NDR Intelligence.
  - *Execution Authority:* ShopDeck / Financial Domain System.

---

## 9. ShopDeck Integration Boundary

ShopDeck remains the authoritative operational truth owner for orders and overall e-commerce state. 

**Inbound (From ShopDeck):**
- Orders (creation and modifications).
- Customer information (identity, contact).
- NDR information (if ShopDeck acts as the aggregator).
- Status changes (cancellations, modifications).

**Outbound (To ShopDeck):**
- Approved resolution actions (e.g., trigger a refund, update an address).
- Communication outcomes (logging the interaction summary).
- Escalation updates (flagging the order for manual review).

*Rule: NDR Intelligence will never create a duplicate ShopDeck database.*

---

## 10. Logistics Integration Boundary

NDR Intelligence relies on logistics systems for execution truth regarding physical movement.

**Integration Points:**
- **Delivery attempt information:** When and where the attempt was made.
- **Failure reasons:** Standardized and raw courier exception codes.
- **Courier updates:** Constraints, SLAs, and capabilities (e.g., does this courier support scheduled delivery?).
- **Resolution feedback:** Acknowledgment that the resolution action (e.g., retry) was accepted or rejected.

---

## 11. Conceptual Data Models

The NDR Intelligence domain stores intelligence data, not operational truth. Conceptual entities include:

- **NDR Case:** The orchestration wrapper tracking the state of the resolution workflow.
- **NDR Event:** The trigger detailing the delivery failure.
- **Customer Interaction:** The semantic log of the back-and-forth communication.
- **Resolution Recommendation:** The formulated decision proposed by the Decision Engine.
- **Escalation Record:** The snapshot of context at the moment human intervention was requested.
- **Outcome Record:** The final analysis of whether the intervention succeeded or failed.

*(Note: Specific database schemas are explicitly excluded.)*

---

## 12. Learning Loop

NDR Intelligence continuously improves the ecosystem's performance:
- **Successful resolutions:** Reinforce the context and decision pathways in the Memory Framework.
- **Failed resolutions:** Flag reasoning gaps or policy failures for review.
- **Customer response patterns:** Improve intent recognition accuracy.
- **Courier patterns:** Help identify systemic logistics issues (e.g., frequent false attempts by a specific provider).

*Rule: Learning improves intelligence; learning does not modify operational truth.*

---

## 13. Security and Governance

- **Customer Privacy:** PII retrieved for context must be tokenized or masked when interacting with external LLMs via the Model Gateway.
- **Conversation Security:** All customer communications must be authenticated and secured.
- **Decision Audit:** Every automated resolution decision must log the exact context and reasoning trace that led to it.
- **Human Approval Requirements:** High-value orders, specific failure types, or complex resolutions mandate human-in-the-loop (HITL) approval before execution.

---

## 14. NDR Architectural Decisions

### Decision: NDR Case Ownership
**Status:** CLOSED
**Decision:** NDR Intelligence owns the intelligence lifecycle of an NDR case (understanding, resolution intelligence, customer interaction intelligence, escalation recommendation, outcome analysis). Business systems continue to own order truth, shipment truth, and delivery execution truth.
**Explanation:** An NDR case in the intelligence layer is not a replacement for operational shipment/order records.

### Decision: NDR Decision Authority
**Status:** CLOSED
**Decision:** NDR Intelligence recommends resolutions and actions (e.g., retry delivery, customer verification, escalation). Business systems retain execution authority.
**Explanation:** Shipment updates, order changes, and refund actions must be executed by the responsible Business Domain System. AI intelligence does not become operational authority.

### Decision: NDR Learning Ownership
**Status:** CLOSED
**Decision:** NDR Intelligence learns from outcomes (successful/failed resolutions, customer responses, courier patterns) to improve future recommendations.
**Explanation:** Learning must not modify operational truth, override business systems, or create duplicate operational databases.

### Decision: Communication Channel Independence
**Status:** CLOSED
**Decision:** NDR Intelligence remains independent from communication channels. It should work with future channels (Voice, Chat, WhatsApp, etc.) through integration boundaries.
**Explanation:** The channel implementation decision remains outside this domain.

---

## 14.1 Remaining Open Decisions

### Voice Channel Architecture
**Status:** OPEN
**Reason:** Requires integration and infrastructure decisions. NDR Intelligence only defines communication intelligence, not transport implementation.

### Telephony Provider Selection
**Status:** OPEN
**Reason:** Vendor/infrastructure decision.

### Human Escalation System
**Status:** OPEN
**Reason:** NDR Intelligence defines escalation intelligence. The support workflow/ticketing implementation belongs to integration architecture.

### AI Evaluation Framework
**Status:** OPEN
**Reason:** Exact benchmarks and evaluation tooling require real operational data.

### Real-Time vs Asynchronous Processing
**Status:** OPEN
**Reason:** Depends on channel requirements, volume, latency needs, and operational SLAs.

---

## 15. NDR Case State Model

**Purpose:**
Define the lifecycle state machine of an NDR Intelligence case. The NDR Case State Model belongs exclusively to NDR Intelligence. It must not become a generic Brain Core workflow engine.

### State Flow

1. **Case Created**
   - *Purpose:* Initialize a new NDR intelligence orchestration wrapper.
   - *Entry Conditions:* An inbound NDR event is received from the Logistics Domain.
   - *Exit Conditions:* Basic case ID and timestamps are assigned.
   - *Responsible Component:* NDR Case Management.
   - *Possible Next States:* Context Gathering.

2. **Context Gathering**
   - *Purpose:* Assemble all necessary operational and intelligence data to formulate an outreach strategy.
   - *Entry Conditions:* Case is created.
   - *Exit Conditions:* Order, shipment, and customer history are successfully fetched via Brain Core.
   - *Responsible Component:* Context Engine (orchestrated by NDR Intelligence).
   - *Possible Next States:* Customer Contact Pending.

3. **Customer Contact Pending**
   - *Purpose:* Await the appropriate channel and time to reach out to the customer.
   - *Entry Conditions:* Context is assembled and failure reason is understood.
   - *Exit Conditions:* Outreach message is sent to the customer.
   - *Responsible Component:* Customer Communication Intelligence.
   - *Possible Next States:* Customer Responded, Escalated.

4. **Customer Responded**
   - *Purpose:* Acknowledge receipt of the customer's reply.
   - *Entry Conditions:* Inbound message from the customer communication channel.
   - *Exit Conditions:* Message is queued for intent analysis.
   - *Responsible Component:* Customer Communication Intelligence.
   - *Possible Next States:* Intent Understood, Escalated.

5. **Intent Understood**
   - *Purpose:* Translate the customer's raw response into a structured business intent.
   - *Entry Conditions:* Customer response is analyzed by the Reasoning Engine.
   - *Exit Conditions:* A clear, high-confidence intent (e.g., "Address Update") is determined.
   - *Responsible Component:* Reasoning Engine (orchestrated by NDR Intelligence).
   - *Possible Next States:* Resolution Recommended, Customer Contact Pending (if clarification needed), Escalated.

6. **Resolution Recommended**
   - *Purpose:* Formulate the optimal business action based on the understood intent and policies.
   - *Entry Conditions:* Intent is understood and mapped to a valid resolution path by the Decision Engine.
   - *Exit Conditions:* A specific execution request is drafted.
   - *Responsible Component:* Resolution Intelligence / Decision Engine.
   - *Possible Next States:* Action Pending, Escalated.

7. **Action Pending**
   - *Purpose:* Await the execution of the recommended action by the authoritative Business Domain.
   - *Entry Conditions:* Execution request is dispatched via the Action Engine.
   - *Exit Conditions:* An acknowledgment or event is received from the Business Domain.
   - *Responsible Component:* Action Engine (orchestrated by NDR Intelligence).
   - *Possible Next States:* Action Executed, Escalated, Failed.

8. **Action Executed**
   - *Purpose:* Confirm the business system has processed the request.
   - *Entry Conditions:* Business Domain confirms the action (e.g., address updated).
   - *Exit Conditions:* The execution is logged and the case is evaluated for final closure.
   - *Responsible Component:* NDR Case Management.
   - *Possible Next States:* Success, Failed.

9. **Success** / **Failed** / **Escalated** / **Closed**
   - *Purpose:* Terminal states marking the end of the NDR Intelligence orchestration loop.
   - *Entry Conditions:* Final logistics outcomes received (Delivered = Success, RTO = Failed, Human Hand-off = Escalated).
   - *Exit Conditions:* Case is locked.
   - *Responsible Component:* Outcome Intelligence.
   - *Possible Next States:* None (Terminal).

**State Transitions and Auditing:**
- *Triggers:* State transitions are triggered either internally by intelligence components completing a task or externally by inbound events (e.g., customer replies, courier updates).
- *Auditing:* Every state transition is immutably logged with its timestamp, triggering event, and contextual snapshot. This audit trail is stored as intelligence memory, not operational truth.

---

## 16. NDR Intelligence Success Metrics

Measurable outcomes used to evaluate the performance of the NDR Intelligence domain.

### Operational Metrics
- **NDR Reduction Percentage:** The percentage decrease in overall NDR cases. *Why it matters:* Indicates proactive interventions are working.
- **RTO Reduction Percentage:** The percentage decrease in Return to Origin shipments. *Why it matters:* Directly maps to cost savings and revenue recovery.
- **Successful Delivery Reattempt Percentage:** The rate at which a second attempt results in delivery. *Why it matters:* Proves the resolution intelligence is choosing the right actions.
- **Average Resolution Time:** The time from NDR Event Received to Action Executed. *Why it matters:* Faster resolutions reduce customer anxiety and courier storage times.

### Customer Experience Metrics
- **Customer Response Rate:** The percentage of customers who reply to automated outreach. *Why it matters:* Indicates the communication intelligence is engaging and timely.
- **Customer Satisfaction (CSAT):** Feedback scores post-resolution. *Why it matters:* Ensures automation doesn't degrade the brand experience.
- **Escalation Rate:** The percentage of cases requiring human handoff. *Why it matters:* A lower rate indicates higher automation efficiency.
- **Resolution Acceptance Rate:** The percentage of customers agreeing with the proposed resolution. *Why it matters:* Proves intent understanding is accurate.

### Intelligence Performance Metrics
- **Resolution Recommendation Acceptance Rate:** The rate at which the business domain accepts and successfully executes the recommended action. *Why it matters:* Ensures AI recommendations align with strict business constraints.
- **AI Decision Accuracy:** A sample-based audit metric evaluating if the Decision Engine made the objectively correct choice. *Why it matters:* Measures the core competency of the intelligence logic.
- **Human Override Percentage:** How often a human agent countermands an automated decision. *Why it matters:* Identifies gaps in the Knowledge or Reasoning engines.
- **Intent Recognition Accuracy:** The success rate of correctly classifying customer intent. *Why it matters:* Prevents frustrating conversational loops.

---

## 17. NDR Decision Intelligence Framework

NDR Intelligence determines recommended resolutions by evaluating:
- **Context factors:** Current location, timeline, and logistics constraints.
- **Customer intent:** The explicitly stated or implicitly derived goal of the customer.
- **Business policies:** Rules dictating acceptable outcomes (e.g., maximum allowed delivery attempts).
- **Historical resolution patterns:** Outcomes of similar past NDR cases.
- **Risk factors:** Fraud probability, location reliability.
- **Confidence assessment:** The statistical certainty that the generated resolution is correct.

**Recommendation Generation vs. Execution Authority:**
NDR Intelligence is strictly responsible for *recommendation generation*. It analyzes the factors above and formulates the optimal action. *Execution authority* belongs exclusively to the Business Domain Systems (e.g., ShopDeck, Logistics systems), which evaluate the recommendation against deterministic business rules before altering operational truth.

---

## 18. NDR Priority and Risk Model

To intelligently route and resolve cases, NDR Intelligence evaluates the following conceptual factors:
- **Order value:** The financial impact of the shipment.
- **Customer importance:** VIP status, lifetime value, or risk of churn.
- **Previous delivery attempts:** The history of failures on the current shipment.
- **Customer sentiment:** Detected frustration or urgency in communication.
- **Courier reliability:** The historical success rate of the assigned logistics partner in the specific region.
- **Delivery probability:** The likelihood of a successful final delivery if an intervention is attempted.
- **Business impact:** The holistic cost of a successful resolution vs. an RTO.

*These factors serve an intelligence purpose only. Specific formulas and implementation logic are excluded from this architectural specification.*

---

## 19. Human Escalation Intelligence

NDR Intelligence continuously monitors cases to determine if automated resolution is insufficient. The domain will recommend human intervention under the following conditions:
- **Customer requested human support:** Explicit requests for a live agent.
- **Low AI confidence:** The Reasoning or Decision Engine cannot confidently formulate an intent or resolution.
- **High-value orders:** Shipments exceeding a defined financial threshold requiring manual review.
- **Policy exceptions:** Situations where the optimal resolution conflicts with standard automated business policies.
- **Negative sentiment:** Extreme customer frustration detected in the conversational thread.
- **Repeated unsuccessful resolution attempts:** Failure of previous automated interventions to close the case.

**Clarification:**
NDR Intelligence only *recommends* escalation by flagging the case. The actual human workflow execution and ticket management belong to operational support systems.

---

## 20. NDR Learning Feedback Requirements

To continuously improve reasoning and decision accuracy, NDR Intelligence must capture the following outcomes:
- **Successful resolution patterns:** Which interventions led to successful deliveries.
- **Failed resolution patterns:** Which interventions resulted in an RTO despite attempts.
- **Customer response patterns:** How customers react to specific outreach channels and messages.
- **Courier behaviour patterns:** Identifying systemic fake delivery attempts or regional anomalies.
- **Decision accuracy:** Validating whether the AI's recommendation was the objectively correct business choice.

**Governance:**
This learning loop strictly improves intelligence (e.g., updating embeddings, prompt context, and knowledge retrieval). The learning process does not modify, create, or alter any operational truth within the Business Domain Systems.
