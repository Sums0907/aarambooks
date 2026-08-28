# Inventory Query Lifecycle Architecture

This document explicitly maps the execution lifecycle across the ecosystem boundaries for a standard intelligence query.

## Example Query: "Give me Low Stock SKU list"

### 1. Ingestion & Semantic Understanding
*Goal: Understand what the user wants in business terms.*

1. **[User]** → Submits query: *"Give me Low Stock SKU list"*
2. **[Intelligence Domain]** (Inventory Intelligence) → Receives the raw natural language query.
3. **[Azm]** (Inventory Semantic Knowledge) → The domain consults Azm to retrieve the business vocabulary. Azm provides the definitions for "Low Stock" and "SKU".
4. **[Cognitive LLM]** → The Intelligence Domain uses the Cognitive LLM to parse the intent. It combines the raw query with the Azm definitions to deduce a structured intent: *"The user is looking for an inventory availability report where quantity is below a certain threshold."*

### 2. Context Requirement Formulation
*Goal: Define exactly what evidence is needed to fulfill the intent.*

5. **[Intelligence Domain]** → Based on the parsed intent, the domain constructs a formal `ResolvedSemanticRequirement`. It specifies the Capability URN (`urn:aaram:capability:inventory:availability`) and the logical constraints (e.g., `quantity < threshold`).

### 3. Generic Routing & Transport
*Goal: Securely request the evidence without knowing the database structure.*

6. **[Brain Core]** (Semantic Infrastructure) → Receives the `ResolvedSemanticRequirement` from the domain.
7. **[Brain Core]** → Checks its `ProviderRegistry` and identifies that the `AaramInventory` business system owns this capability. 
8. **[Brain Core]** → Acquires an M2M (Machine-to-Machine) token for authorization and routes the generic request over the network.

### 4. Physical Translation & Execution
*Goal: Fetch the physical truth from the database.*

9. **[CEM]** (AaramInventory Context Exposure Module) → Receives the generic HTTP request from Brain Core.
10. **[CEM]** → Applies its internal **Semantic Identity → Physical Reality Mapping**. It translates the abstract requirement into a physical operational query (e.g., `SELECT sku, quantity FROM tbl_stock WHERE quantity < 10`).
11. **[CEM]** → Executes the query against the AaramInventory database.
12. **[CEM]** → Wraps the raw results into an opaque JSON payload, attaches gap/sufficiency metadata, and returns it as an `EvidenceItem`.

### 5. Evidence Delivery
*Goal: Return the truth to the requester.*

13. **[Brain Core]** → Receives the `EvidenceItem` from the CEM. It attaches provenance ("This came from AaramInventory at timestamp X") and returns the package to the Intelligence Domain.

### 6. Reasoning & Synthesis
*Goal: Turn raw data into business intelligence.*

14. **[Intelligence Domain]** → Receives the raw JSON evidence package.
15. **[Reasoning LLM]** → The domain injects the JSON evidence and domain-specific rules (e.g., "Format as a bulleted list") into the Reasoning LLM.
16. **[Reasoning LLM]** → Synthesizes the facts into a clear, conversational answer without hallucinating numbers not present in the evidence.
17. **[Intelligence Domain]** → Delivers the final response to the user: *"Here is your Low Stock SKU list..."*

***

## Visual Architecture Map

```text
USER QUERY
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ INTELLIGENCE DOMAIN (Inventory Intelligence)            │
│   ├── Consults: Azm (Vocabulary/Concepts)               │
│   ├── Parses Intent via: Cognitive LLM                  │
│   ├── Formulates: ResolvedSemanticRequirement           │
│   └── Synthesizes final response via: Reasoning LLM     │
└──────────────────────────┬──────────────────────────────┘
                           │ 
                           ▼ (Semantic Request)
┌─────────────────────────────────────────────────────────┐
│ BRAIN CORE (Semantic Infrastructure)                    │
│   ├── Resolves Capability Owner via ProviderRegistry    │
│   ├── Handles M2M Auth                                  │
│   └── Routes abstract request                           │
└──────────────────────────┬──────────────────────────────┘
                           │ 
                           ▼ (Generic HTTP Payload)
┌─────────────────────────────────────────────────────────┐
│ AARAMINVENTORY CEM (Business System Boundary)           │
│   ├── Translates generic payload to physical SQL        │
│   ├── Executes against physical Database                │
│   └── Returns raw EvidenceItem                          │
└─────────────────────────────────────────────────────────┘
```
