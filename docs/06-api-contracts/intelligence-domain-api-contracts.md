# Intelligence Domain API Contracts

## Purpose

This document defines the conceptual communication contract between Aaram Brain Intelligence Domains and the shared intelligence capabilities (Brain Core) they consume.

The purpose of this contract is to establish how business-specific intelligence domains collaborate with Brain Core while preserving ownership boundaries.

The governing principle is:

> Business systems create truth. Aaram Brain creates intelligence from that truth.

---

# Architectural Position

Aaram Brain consists of:
- Brain Core.
- Intelligence Domains (e.g., NDR Intelligence, Customer Query Intelligence).

Intelligence Domains are specialized reasoning applications that solve specific business objectives by consuming Brain Core capabilities.

```text
Business Objective
        |
        ↓
Intelligence Domain
        | (Semantic Intent)
        ↓
Brain Core Capabilities
        | (Generic Capabilities / Opaque JSON Evidence)
        ↓
Intelligence Outcome
```

---

# Intelligence Domain Responsibilities

Intelligence Domains are responsible for:
- Defining domain-specific business objectives.
- Formulating **Semantic Intents** (e.g., "I need the delivery attempts for AWB 123").
- Interpreting the opaque JSON evidence injected into the LLM context window by Brain Core.
- Managing domain-specific intelligence workflows.

Intelligence Domains do not:
- Hardcode physical business database schemas (e.g., `InventoryContext`).
- Directly modify Business System data.

---

# Information Exchange Model (Stage F)

## Context Request
Intelligence Domains request context from Brain Core using the **Context Capability Architecture**.
- The Domain emits a `SemanticRequirement` (e.g., `urn:aaram:capability:fulfillment:tracking`).
- Brain Core resolves this against the Business System and returns an `EvidenceItem`.
- **Constraint:** The Intelligence Domain MUST NOT attempt to parse the `EvidenceItem.data_payload` into a rigid Pydantic struct. It must rely on the Reasoner (LLM) to extract insights from the raw JSON payload injected into the prompt.

*(Legacy Exception: During the Stage F.1 transition, Orchestrators currently receive `CustomerContext` and `ShipmentContext` directly from the Event Bus. This is a recognized architectural debt that will be migrated to the generic Semantic Context flow in a future phase.)*

---

# Producer and Consumer Responsibilities

## Intelligence Domain as Consumer
Responsible for:
- Requesting appropriate generic capabilities.
- Supplying accurate `SemanticConstraints` (identifiers, operators).
- Applying returned JSON intelligence correctly via LLM reasoning.
- Maintaining domain-specific workflow behavior.

## Brain Core as Provider
Responsible for:
- Sourcing context via the `ContextCapabilityGateway`.
- Securing interactions with M2M tokens.
- Returning explainable, source-attributed `EvidenceItems` to prevent LLM hallucination.

---

# Domain Isolation Principle

Each Intelligence Domain remains independent. NDR Intelligence does not directly query Customer Query Intelligence. If domains must share insights, they do so by persisting their conclusions to the Business System (truth owner), which can then be retrieved by the other domain via standard Brain Core capability requests.

---

# Final Contract Principle

Intelligence Domains apply intelligence using abstract semantic queries.
Brain Core routes those queries to physical truth owners via generic capabilities.
Business Systems remain exclusive owners of operational truth.
Contracts enable collaboration without transferring schema ownership.
