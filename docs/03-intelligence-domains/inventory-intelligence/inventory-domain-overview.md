# Inventory Intelligence Domain Overview

## 1. Domain Purpose

The Inventory Intelligence Domain exists to orchestrate, understand, and resolve complex natural-language questions regarding the inventory, warehousing, and fulfillment operations of the AaramBooks ecosystem.

**Business Problem:** 
Inventory data is traditionally locked behind complex database schemas (ledgers, jobwork, exceptions, balances). Answering business-critical questions currently requires manual forensic accounting across multiple screens.

**Why This Domain Exists:** 
To provide a specialized intelligence application capable of:
1. Accepting an arbitrary natural-language inventory question.
2. Understanding what the user is asking.
3. Determining the inventory business context required to answer it.
4. Declaring that context requirement to Brain Core's Context Layer.
5. Reasoning over the returned business truth.
6. Returning useful inventory intelligence.

## 2. Correct Responsibility Separation

### A. What Inventory Intelligence Owns:
- Natural-language understanding and inventory intent interpretation.
- Determining *what* business context is required to answer the question.
- Inventory-specific reasoning over obtained context.
- Deterministic calculations (e.g., yield, COGS).
- Comparison, aggregation, and anomaly interpretation.
- Business insight synthesis and answer composition.
- Evidence and confidence semantics.

### B. What Brain Core (Generic Infrastructure) Owns:
- **Context Layer:** Resolving and orchestrating context requirements.
- Governed access to business truth (Context Providers).
- LLM gateway, memory/knowledge infrastructure, and generic orchestration primitives.
- Security and identity integration.

### C. What AaramInventory Owns:
- Authoritative inventory business truth.
- Inventory domain rules, transactional state, and master data.
- Inventory ledger and operational records.

### What the Domain Does NOT Own:
- **Inventory Data / Truth:** It does NOT own inventory truth and MUST NOT become an inventory database.
- **Transport Mechanisms:** The Intelligence Domain does NOT know or care whether context is obtained via REST API, a read endpoint, an internal service adapter, or a read model. Transport is an implementation detail below the Context abstraction.
- **Operational Mutability:** It does NOT directly mutate inventory. AaramInventory remains the SYSTEM OF RECORD.

## 3. The Context Capability Abstraction

The architecture strictly separates the domain from underlying APIs:

```text
Natural Language 
  → Inventory Intelligence 
    → Declares Required Context 
      → Brain Core Context Layer 
        → Authoritative AaramInventory Business Truth 
          → Context Returned 
            → Inventory Reasoning 
              → Intelligence
```

The Intelligence Domain must **not** be designed around individual AaramInventory APIs. If a required context is not available, it is a **Context Capability Gap** in the Context Layer, NOT a limitation of the Intelligence Domain.

## 4. The Generality Principle

While there exists a predefined set of 17 evaluation questions, these are *representative evaluation scenarios* used to prove that the generic domain works. The architecture must remain generic enough to answer *new* inventory questions that were never included in the original evaluation set. 
