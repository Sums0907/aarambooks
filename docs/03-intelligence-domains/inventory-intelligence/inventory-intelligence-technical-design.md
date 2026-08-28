# Inventory Intelligence Technical Design Specification

## 1. Architectural Distinctions

To ensure correct separation of concerns, the design explicitly distinguishes between:

- **A. Business Truth:** Owned entirely by AaramInventory.
- **B. Context Capability:** The governed mechanism in Brain Core's Context Layer by which authoritative business truth is obtained and made available to Intelligence Domains.
- **C. Intelligence Domain:** Consumes the contextual business truth and reasons over it.
- **D. Transport:** An implementation detail (e.g., REST API, gRPC, direct database read) completely hidden below the context abstraction layer. The Intelligence Domain does NOT depend on or understand transport.

---

## 2. Generic Query → Context → Reasoning Model

The domain processes arbitrary natural-language inventory questions through a strict lifecycle:

1. **Natural-language question:** An inbound question is received.
2. **Understand question:** The domain parses the intent and identifies the entities involved.
3. **Determine required inventory context:** The domain determines *what* facts are needed.
4. **Build context requirement:** The domain declares this requirement to the Brain Core Context Layer.
5. **Context Resolution (Brain Core):** The Context Layer determines *how* to obtain the truth and delegates to a Context Provider to fetch it from AaramInventory.
6. **Validate returned truth:** The domain ensures the returned facts are sufficient to answer the question.
7. **Inventory-specific reasoning:** The domain applies business logic (deterministic calculations or LLM reasoning) over the facts.
8. **Generate useful intelligence:** Synthesize findings into clear insights.
9. **Structured/domain response:** Formulate the final output.

---

## 3. Inventory Context Capabilities

The domain relies on an expandable vocabulary of Context Capabilities. If a capability is missing, it is identified as a **Context Capability Gap** in the Context Layer. 

Examples of conceptual context capabilities the domain may require:
- **SKU/Catalog Context:** Master data, physical dimensions, BOM/product structure.
- **Warehouse Context:** Location metadata.
- **Inventory Availability:** Current physical stock balances.
- **Inventory Movements & Stock History:** Historical ledger of ins and outs.
- **Inventory Exceptions:** Discrepancies, negative balances, and count variances.
- **Jobwork Context:** Raw material issues, receipts, and material reconciliation.
- **Production Readiness:** BOM availability against current stock.
- **Inventory Ledger & Valuation:** COGS and financial value.

---

## 4. Deterministic vs LLM Responsibilities

**Deterministic (Code/Math):**
- Arithmetic (yield, COGS).
- Aggregation (summing movements) and Comparisons (stock A > stock B).
- Filtering, ranking, threshold evaluation, and factual extraction from context.

**LLM / Domain Reasoning:**
- Understanding ambiguous natural language and user intent.
- Deciding which context capabilities are required.
- Synthesizing multiple facts into cohesive narrative insights.
- Explaining results naturally.
- *CRITICAL RULE: The LLM must NEVER invent, estimate, or hallucinate inventory facts, movements, or balances.*

---

## 5. Error & Safety Boundaries

The domain must fail honestly rather than fabricate an answer.
- **Context Capability Gap:** If the domain determines it needs context that the Brain Core Context Layer cannot currently provide, the domain explicitly reports a Context Capability Gap (e.g., "This query requires jobwork movement context, which is currently unavailable to the intelligence layer").
- **LLM Failure / Hallucination Detection:** Fallback to safe, generic inability-to-answer message.
- **Conflicting Context:** Highlight conflicts without inventing resolutions (e.g., "Ledger shows 50 units, but physical balance shows 0").

---

## 6. Dependencies

**Brain Core:**
- Context Layer (for resolving required context).
- AI Gateway (LiteLLM) and generic orchestration.

**AaramInventory:**
- Authoritative inventory business truth (isolated behind the Context Layer).

**AaramIdentity:**
- Authentication through the finalized ecosystem M2M contract (`aaram_brain` ServiceAccount, `AARAM_BRAIN_CORE` role, with existing 5 permissions).

---

## 7. Implementation Readiness

**Implementation is blocked by Context Capability Gaps, not by domain design limits.**
Inventory Intelligence implementation depends on the maturity of the required Context Capabilities. Missing business contexts are Context Capability Gaps and should be addressed in the Context Layer rather than by weakening or constraining the Intelligence Domain.

- **Domain Design Readiness:** Architecturally ready.
- **Context Capability Readiness:** Partially complete (basic inventory balance availability exists; movements, ledgers, and jobwork represent capability gaps).
- **Implementation Readiness:** Blocked pending Context Layer maturation for complex scenarios.
