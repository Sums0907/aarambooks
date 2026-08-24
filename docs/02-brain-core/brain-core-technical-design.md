# Brain Core Technical Design Specification

## Overview

Aaram Brain Core is the centralized intelligence foundation of the AaramBooks ecosystem. It is generic, domain-independent, and reusable by multiple Intelligence Domains (e.g., NDR Intelligence, Customer Query Intelligence). Brain Core provides raw intelligence capabilities but contains no business-specific workflows.

---

## 1. Context Engine

**Responsibilities:**
Assembles situational understanding by dynamically aggregating and fusing relevant data points before reasoning occurs.

**Context Assembly Principles:**
The engine pulls data from operational business systems to build a transient snapshot of the situation. Context provides understanding but does not own or modify operational truth.

**Context Types Assembled:**
- **Customer Context:** Identity, profile, and explicit account details (from AaramIdentity/ShopDeck).
- **Order Context:** Line items, value, and current operational state (from ShopDeck).
- **Shipment Context:** Carrier, tracking ID, and delivery attempts (from Logistics).
- **Product Context:** Specifications and catalog attributes (from ShopDeck).
- **Conversation Context:** Multi-turn dialog states (from Memory Framework).
- **Historical Interaction Context:** Previous queries, sentiments, and resolved issues (from Memory Framework).

---

## 2. Memory Framework

**Responsibilities:**
Enables Brain Core to retain context and learn across disparate interactions without becoming a transactional ledger. Memory improves intelligence; memory never becomes operational truth.

**Memory Types:**
- **Conversation Memory:** The semantic log and state of an ongoing multi-turn interaction.
- **Interaction Memory:** Historical interactions across all channels.
- **Resolution Memory:** Outcomes of past AI recommendations (successes vs. failures).
- **Preference Memory:** Implicitly derived customer preferences (e.g., tone, contact timing).
- **Intelligence Pattern Memory:** Aggregate learned patterns (e.g., specific courier failure rates).

---

## 3. Knowledge Engine

**Responsibilities:**
Acts as the intelligence layer over static business rules, policies, and product manuals.

**Capabilities:**
- **Knowledge Retrieval:** Dynamically finding the most relevant policies or SOPs for a given context.
- **Knowledge Understanding:** Parsing unstructured business text into structured rules for reasoning.
- **Knowledge Grounding:** Ensuring AI responses are strictly bound by approved company policies.

**Clarification:**
Business Domains own the knowledge content (the actual policies and documents). Brain Core owns the intelligence, indexing, and retrieval capabilities over that knowledge.

---

## 4. Reasoning Engine

**Responsibilities:**
Analyzes assembled context against retrieved knowledge to interpret meaning.

**Capabilities:**
- **Situation Analysis:** Interpreting the current operational state (e.g., "Why did this delivery fail?").
- **Intent Understanding:** Parsing raw customer input into structured business goals (e.g., `Address Update`).
- **Pattern Recognition:** Identifying systemic anomalies based on historical context.
- **Possibility Evaluation:** Generating potential paths forward based on knowledge grounding.

**Clarification:**
Reasoning interprets data. It does not execute business actions.

---

## 5. Decision Engine

**Responsibilities:**
Evaluates the outputs of the Reasoning Engine against business constraints to determine the optimal course of action.

**Decision Output Includes:**
- **Recommendation:** The specific proposed outcome (e.g., "Retry Delivery").
- **Confidence:** Statistical certainty of the decision's correctness.
- **Reasoning:** An auditable trace of why this decision was chosen based on context and policy.
- **Required Action:** The specific API intent required to execute the recommendation.

**Clarification:**
The Decision Engine strictly *recommends*. Business Domain Systems retain absolute authority to execute.

---

## 6. Action Engine

**Responsibilities:**
Translates intelligence recommendations into controlled, standardized execution requests for Business Domain Systems.

**Action Lifecycle:**
1. **Intelligence Domain** 
   ↓
2. **Brain Core Action Engine** (Formats request)
   ↓
3. **Business Domain API** (Transmits request)
   ↓
4. **Business Domain Validation** (Evaluates against rules)
   ↓
5. **Execution** (Modifies truth)

**Clarification:**
The Action Engine never directly changes operational data.

---

## 7. Model Gateway

**Responsibilities:**
Provides a strict abstraction and governance layer between internal Aaram-owned intelligence capabilities and external AI infrastructure.

**Boundary Management:**
The gateway manages connections to external providers for:
- LLMs (Language modeling and reasoning).
- STT (Speech-to-Text).
- TTS (Text-to-Speech).
- Telephony integration capabilities.

It enforces vendor independence, token limits, PII masking, safety filtering, and telemetry logging before queries leave the ecosystem.

---

## 8. Brain Core Non-Responsibilities

**Purpose:**
Explicitly define boundaries to protect Brain Core from architectural drift. Brain Core provides generic intelligence capabilities and must never act as a business system of record.

**Brain Core must never:**
- Own customer master data.
- Own orders.
- Own inventory.
- Own warehouse execution.
- Own refunds.
- Execute operational transactions directly.
- Become a CRM/ERP replacement.
- Contain Intelligence Domain workflows (e.g., NDR workflows and customer support workflows strictly belong to Intelligence Domains).

---

## 9. Open Decisions

The following architectural and physical implementation decisions remain undecided and are marked **[OPEN]**:

- **Database selection:** The physical database technology (e.g., Vector DB for embeddings, NoSQL for conversation history) for the Memory Framework.
- **Internal protocol:** The specific communication protocol (e.g., gRPC vs REST) between Intelligence Domains and Brain Core.
- **External AI Providers:** The specific vendors chosen for LLMs, STT, TTS, and Telephony.

---

## 10. Brain Core Intelligence Flow

The generic Brain Core processing flow is:

1. **Input Event / Request**
   ↓
2. **Context Assembly**
   ↓
3. **Knowledge Retrieval**
   ↓
4. **Reasoning**
   ↓
5. **Decision Recommendation**
   ↓
6. **Action Request (if required)**
   ↓
7. **Business Domain Execution**
   ↓
8. **Outcome Feedback**
   ↓
9. **Memory Update**

**Rules:**
- Brain Core may understand and recommend.
- Business Domains execute operational changes.
- Outcomes improve future intelligence.
