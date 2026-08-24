# Business System API Contracts

## Purpose

This document defines the conceptual communication contract between Aaram Brain / Intelligence Domains and Business Systems that own operational truth.

The purpose of this contract is to establish how intelligence capabilities can consume trusted business information and request controlled execution while preserving ownership boundaries.

This document does not define technical API specifications, implementation details, schemas, infrastructure, or technology choices.

The governing principle is:

> Business systems create truth. Aaram Brain creates intelligence from that truth.

---

# Architectural Position

Business Systems and Aaram Brain have separate responsibilities.

Business Systems:

- Execute operational workflows.
- Maintain authoritative business information.
- Own domain truth.

Aaram Brain:

- Understands business information.
- Provides intelligence capabilities.
- Creates recommendations and action requests.

The relationship is:

```
Business Systems
        |
        ↓
Operational Truth
        |
        ↓
Aaram Brain Intelligence
        |
        ↓
Recommendations / Action Requests
```

Communication enables collaboration without transferring ownership.

---

# Contract Responsibility

Business System contracts define:

- Information available for intelligence processing.
- Capabilities exposed by business domains.
- Controlled requests that intelligence systems may submit.
- Responsibilities of producers and consumers.

The contract does not define:

- Business ownership transfer.
- Duplicate truth storage.
- Intelligence ownership.
- Internal business workflows.

---

# Business System Responsibilities

Business Systems are responsible for:

- Maintaining operational truth.
- Validating business rules.
- Executing approved operations.
- Recording authoritative outcomes.

Examples:

## AaramIdentity

Owns:

- Identity information.
- Authentication information.
- Authorization information.

## AaramInventory

Owns:

- Product information.
- Inventory state.
- Stock movements.
- Inventory ledger.

## AaramPacking

Owns:

- Warehouse execution information.
- Packing workflows.
- Packing events.

Business Systems do not delegate ownership of truth to Aaram Brain.

---

# Aaram Brain Responsibilities

Aaram Brain consumes Business System capabilities to:

- Understand business situations.
- Assemble context.
- Perform reasoning.
- Support decision intelligence.
- Generate controlled action requests.

Aaram Brain does not:

- Modify operational databases directly.
- Become a system of record.
- Replace operational workflows.

---

# Information Access Contract

Business Systems may provide operational information required for intelligence processing.

Examples:

- Customer information.
- Order information.
- Inventory information.
- Warehouse execution information.
- Shipment information.

The information remains owned by the responsible Business System.

Using information does not create ownership.

---

# Operational Action Contract

Intelligence systems may request operational actions through approved communication boundaries.

The flow is:

```
Intelligence Domain
        |
        ↓
Action Request
        |
        ↓
Business System Validation
        |
        ↓
Business System Execution
        |
        ↓
Operational Truth Update
```

Business Systems are responsible for:

- Validating requests.
- Applying business rules.
- Executing changes.
- Returning authoritative outcomes.

---

# Producer and Consumer Responsibilities

## Business System as Producer

Responsible for:

- Providing trusted operational information.
- Maintaining data correctness.
- Defining domain-owned capabilities.

---

## Intelligence Layer as Consumer

Responsible for:

- Using information for intelligence purposes.
- Preserving source ownership.
- Creating recommendations based on available context.

---

# Intelligence Domain Alignment

## NDR Intelligence

Consumes Business System capabilities to understand:

- Delivery situations.
- Shipment context.
- Operational outcomes.

NDR Intelligence does not own shipment truth or delivery execution.

---

## Customer Query Intelligence

Consumes Business System capabilities to understand:

- Customer context.
- Order information.
- Product information.
- Return-related information.

Customer Query Intelligence does not own customer records, orders, or operational workflows.

---

# Ownership Boundaries

The following principles must always remain true:

- Business Systems own operational truth.
- Aaram Brain owns intelligence capabilities.
- Intelligence Domains own business-specific intelligence logic.
- Applications consume intelligence outcomes.

---

# Security and Governance Principles

Business System communication must preserve:

- Access control boundaries.
- Authorization responsibility.
- Auditability.
- Data protection requirements.

Security implementation details remain outside this conceptual contract.

---

# Contract Evolution Principles

Future changes must preserve:

- Single ownership of operational truth.
- Independence of Business Domains.
- Independence of Intelligence Domains.
- Clear communication boundaries.

If a change requires modifying another domain responsibility, it must follow architecture governance.

---

# Unresolved Architectural Decisions

The following areas may require future governance decisions:

## Business Capability Exposure Scope

Which Business System capabilities become stable external contract boundaries.

## Action Approval Boundaries

Which operational actions require human approval before execution.

## Context Access Rules

Which operational information categories may be exposed for intelligence processing.

These decisions do not change the current architecture principles.

---

# Final Contract Principle

Business Systems create and own operational truth.

Aaram Brain consumes that truth to create intelligence.

Contracts enable controlled collaboration.

Contracts do not transfer ownership.
