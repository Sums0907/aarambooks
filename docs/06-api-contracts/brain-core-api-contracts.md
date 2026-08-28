# Brain Core API Contracts

## Purpose

This document defines the conceptual communication contract between Aaram Brain Core and external systems (Intelligence Domains and Business Systems).

The purpose of this contract is to establish how shared intelligence capabilities are communicated while preserving ownership boundaries.

The governing principle is:

> Business systems create truth. Aaram Brain creates intelligence from that truth.

---

# Architectural Position

Aaram Brain consists of:
- Brain Core.
- Intelligence Domains.

Brain Core provides reusable intelligence capabilities. Intelligence Domains apply those capabilities to specific business objectives.

```text
Intelligence Domains
        | (Cognitive Queries)
        ↓
Brain Core Capabilities
        | (Generic Semantic Constraints)
        ↓
Business Systems (CEM)
```

---

# API Contract Boundaries (Stage F Generic Architecture)

With the introduction of the Stage F Generic Context Capability Framework, Brain Core's API contracts have pivoted from physical domain coupling to strict semantic abstraction.

## 1. Brain Core ↔ Business System (Southbound Contract)
Brain Core uses the `ContextCapabilityGateway` to request truth from Business Systems.

- **Request:** Brain Core emits a `ResolvedSemanticRequirement` bound to a specific Capability URN. Brain Core does not know the physical schema of the target database.
- **Response:** The Business System returns an `EvidenceItem` containing an opaque JSON `data_payload`.
- **Constraint:** Business Systems MUST NOT share Pydantic models (like `InventoryContext`) with Brain Core. The contract is strictly JSON over HTTP/gRPC.

## 2. Brain Core ↔ Intelligence Domain (Northbound Contract)
Intelligence Domains orchestrate workflows by requesting capabilities from Brain Core.

- **Request:** Domains issue intent (e.g., "Resolve NDR for tracking XYZ"). 
- **Response:** Brain Core provisions reasoning, semantic resolution, and aggregated Context Capabilities.
- **Constraint:** Domains must rely on the opaque JSON evidence injected into the LLM context window rather than hardcoding against physical domain schemas. *(Note: Legacy transitional models like `CustomerContext` and `ShipmentContext` still temporarily bridge this boundary for Event Bus workflows, but will be deprecated in favor of generic evidence.)*

---

# Producer and Consumer Responsibilities

## Brain Core as Producer (to Domains)
Brain Core is responsible for:
- Capability routing (via `ProviderRegistry`).
- Semantic resolution (translating intent to URNs).
- Injecting context seamlessly into LLM Prompts.

## Business Systems as Producers (to Brain Core)
Business Systems are responsible for:
- Exposing Context Exposure Modules (CEM).
- Translating generic Semantic Constraints into SQL/NoSQL queries.
- Providing authoritative JSON evidence.

## Intelligence Domain as Consumer
Intelligence Domains are responsible for:
- Applying capabilities correctly.
- Domain-specific interpretation of LLM responses.
- Business objective alignment.

---

# Final Contract Principle

Brain Core provides intelligence capabilities via generic, source-blind routing.
Intelligence Domains apply those capabilities.
Business Systems remain exclusive owners of operational truth and physical data schemas.
Contracts enable communication.
Contracts do not transfer data ownership.
