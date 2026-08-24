# Brain Core API Contracts

## Purpose

This document defines the conceptual communication contract between Aaram Brain Core and Intelligence Domains.

The purpose of this contract is to establish how shared intelligence capabilities are communicated while preserving ownership boundaries.

This document does not define technical API specifications, implementation details, schemas, infrastructure, or technology choices.

The governing principle is:

> Business systems create truth. Aaram Brain creates intelligence from that truth.

---

# Architectural Position

Aaram Brain consists of:

- Brain Core.
- Intelligence Domains.

Brain Core provides reusable intelligence capabilities.

Intelligence Domains apply those capabilities to specific business objectives.

The relationship is:

```
Intelligence Domains
        |
        ↓
Brain Core Capabilities
        |
        ↓
Intelligence Support
```

Communication between these layers enables collaboration without transferring responsibility ownership.

---

# Contract Responsibility

The Brain Core contract defines:

- Capabilities that Brain Core makes available.
- Information required to use those capabilities.
- Intelligence outcomes returned to domains.
- Responsibilities of producers and consumers.

The contract does not define:

- Business ownership.
- Operational execution ownership.
- Business workflow ownership.
- Truth ownership.

---

# Brain Core Responsibilities

Brain Core provides shared intelligence capabilities.

Conceptual capabilities include:

- Understanding business context.
- Accessing relevant knowledge capabilities.
- Supporting reasoning.
- Supporting decision intelligence.
- Supporting intelligent action planning.

Brain Core does not own:

- Customer truth.
- Order truth.
- Inventory truth.
- Shipment truth.
- Business process execution.

---

# Intelligence Domain Responsibilities

Intelligence Domains consume Brain Core capabilities to solve specific business problems.

Responsibilities include:

- Defining domain objectives.
- Applying intelligence capabilities to domain scenarios.
- Interpreting intelligence results.
- Creating domain-specific intelligence outcomes.

Intelligence Domains do not transfer business ownership into Brain Core.

---

# Information Exchange Model

## Context Exchange

Intelligence Domains may provide relevant business context required for intelligence processing.

The source of business truth remains the responsible Business System.

Brain Core uses context for understanding and reasoning.

Brain Core does not become the owner of that information.

---

## Knowledge Exchange

Brain Core may provide knowledge capabilities required by Intelligence Domains.

Knowledge capabilities support understanding and reasoning.

They do not create duplicate operational records.

---

## Reasoning Exchange

Intelligence Domains may request reasoning support from Brain Core.

Brain Core supports analysis and intelligence generation.

The Intelligence Domain remains responsible for domain interpretation.

---

## Decision Support Exchange

Brain Core may support decision intelligence.

The resulting intelligence assists domain decisions.

Operational decisions remain governed by the responsible business domain.

---

## Action Intelligence Exchange

Brain Core may support intelligent action planning.

Brain Core does not execute operational business actions directly.

Execution responsibility remains with the responsible Business System through approved communication boundaries.

---

# Ownership Boundaries

## Information Ownership

Business information remains owned by the Business System responsible for that domain.

Examples:

- Customer truth remains with the responsible customer/business system.
- Inventory truth remains with AaramInventory.
- Warehouse execution truth remains with AaramPacking.

Using information does not create ownership.

---

## Intelligence Ownership

Brain Core owns shared intelligence capabilities.

Intelligence Domains own business-specific intelligence logic.

Applications consume intelligence outcomes.

---

# Producer and Consumer Responsibilities

## Brain Core as Producer

Brain Core is responsible for:

- Capability meaning.
- Intelligence consistency.
- Shared intelligence behavior.

---

## Intelligence Domain as Consumer

Intelligence Domains are responsible for:

- Applying capabilities correctly.
- Domain-specific interpretation.
- Business objective alignment.

---

# NDR Intelligence Alignment

NDR Intelligence consumes Brain Core capabilities to support:

- Understanding failed delivery situations.
- Reasoning over available context.
- Supporting resolution intelligence.

NDR Intelligence remains responsible for NDR-specific intelligence behavior.

Brain Core does not own delivery operations or delivery truth.

---

# Customer Query Intelligence Alignment

Customer Query Intelligence consumes Brain Core capabilities to support:

- Understanding customer interactions.
- Reasoning over customer context.
- Supporting intelligent responses.

Customer Query Intelligence remains responsible for customer support intelligence behavior.

Brain Core does not own customer records or support workflows.

---

# Contract Evolution Principles

Future changes must preserve:

- Brain Core generic responsibility.
- Intelligence Domain independence.
- Business System truth ownership.
- Clear producer and consumer boundaries.

If a change requires modifying another module responsibility, it must follow architecture governance.

---

# Unresolved Architectural Decisions

The following areas require governance review before implementation if additional detail is required:

## Brain Core Capability Exposure Scope

Clarify which Brain Core capabilities are stable external contract boundaries versus internal capabilities.

## Action Responsibility Boundary

Clarify the exact responsibility separation between Brain Core action intelligence, Intelligence Domain decisions, and Business System execution.

## Context Availability Rules

Clarify which categories of business context may be exchanged for intelligence processing.

These items do not change current architecture. They represent future decision requirements.

---

# Final Contract Principle

Brain Core provides intelligence capabilities.

Intelligence Domains apply those capabilities.

Business Systems remain owners of operational truth.

Contracts enable communication.

Contracts do not transfer ownership.
