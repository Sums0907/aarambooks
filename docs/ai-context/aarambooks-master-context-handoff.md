# AaramBooks Master Context Handoff

## 1. Purpose of This Document

This document is the authoritative AI onboarding context for the AaramBooks ecosystem.

Its purpose is to provide consistent understanding for:

- ChatGPT architecture discussions.
- Antigravity (AG) implementation context.
- Future developers.
- Future AI agents.

This document does not replace architecture documentation.

It provides the context required to correctly interpret and work with the architecture documents.

---

# 2. Project Identity

## Project Name

AaramBooks

## Definition

AaramBooks is the overarching ecosystem representing the evolution of Aaram into an AI-native business operating system.

AaramBooks consists of two major categories:

## 2.1 Business Domain Systems

Business systems are deterministic operational systems responsible for:

- Maintaining operational truth.
- Executing business processes.
- Preserving domain-specific business rules.

Current business domain systems:

- AaramIdentity
- AaramInventory
- AaramPacking

---

## 2.2 Intelligence Layer

The intelligence layer is represented by Aaram Brain.

Aaram Brain:

- Understands business context.
- Provides reasoning.
- Generates recommendations.
- Enables intelligent automation.

Core principle:

> Business systems create truth. Aaram Brain creates intelligence from that truth.

---

# 3. Core Architectural Philosophy

AaramBooks follows these principles:

## 3.1 Business Systems Own Truth

Every business capability must have a clear owner.

The system responsible for a business domain owns the truth of that domain.

---

## 3.2 Intelligence Does Not Own Truth

AI systems consume trusted business information.

AI should not:

- Replace operational systems.
- Duplicate business databases.
- Become the source of operational truth.

---

## 3.3 Domain Independence

Each business domain should:

- Own its responsibility.
- Evolve independently.
- Avoid unnecessary coupling.

---

## 3.4 Controlled Collaboration

Domains collaborate through clearly defined boundaries.

No domain should directly take ownership of another domain's responsibility.

---

# 4. Existing Systems

## 4.1 AaramIdentity

Purpose:

Identity and access foundation.

Owns:

- Authentication.
- Authorization.
- Users.
- Roles.
- Permissions.

Does not own:

- Business data.
- Inventory.
- Orders.
- Operational workflows.

---

## 4.2 AaramInventory

Purpose:

Inventory truth system.

Owns:

- Product/SKU information.
- Inventory state.
- Stock movements.
- Inventory ledger.
- Inventory-related business truth.

---

## 4.3 AaramPacking

Purpose:

Physical warehouse execution system.

Owns:

- Packing workflows.
- Warehouse execution events.
- Physical operational truth.

---

# 5. Aaram Brain Definition

Aaram Brain is the intelligence and decision layer of AaramBooks.

Aaram Brain is NOT:

- A chatbot platform.
- A replacement ERP.
- A duplicate business database.
- A replacement for operational systems.

Aaram Brain IS:

A reusable intelligence foundation that understands business context, reasons over information, and enables intelligent decisions and automation.

---

# 6. Aaram Brain Structure

```text
Aaram Brain

|
├── Brain Core
|
└── Intelligence Domains
    |
    ├── NDR Intelligence
    |
    └── Customer Query Intelligence
```

---

# 7. Brain Core

Brain Core represents the shared intelligence foundation.

Its purpose:

- Provide reusable intelligence capabilities.
- Enable common understanding across intelligence domains.
- Support future intelligence expansion.

---

# 8. Initial Intelligence Domains

## 8.1 NDR Intelligence

Purpose:

Reduce delivery failures through intelligent handling of unsuccessful delivery situations.

Focus:

- Understanding failed delivery cases.
- Supporting customer conversations.
- Recommending resolution actions.
- Improving delivery success.

---

## 8.2 Customer Query Intelligence

Purpose:

Provide intelligent customer support capabilities.

Focus:

- Order status queries.
- Returns.
- Damaged products.
- Product questions.
- Customer service interactions.

---

# 9. Current Architecture Phase

Current phase:

Architecture First.

The objective is to define:

- Ecosystem boundaries.
- Domain ownership.
- Responsibilities.
- Terminology.
- Integration philosophy.
- Intelligence architecture.

Implementation details are intentionally deferred.

---

# 10. Documentation Roadmap

## Phase 1 — Project Context

Location:

```text
docs/00-project-context/
```

Documents:

- aarambooks-overview.md
- current-state.md
- terminology.md
- vision-and-goals.md
- scope-boundaries.md

Purpose:

Define what AaramBooks is and why it exists.

---

## Phase 2 — Ecosystem Architecture

Location:

```text
docs/01-architecture/
```

Documents:

- ecosystem-architecture.md
- domain-ownership.md
- system-boundaries.md
- integration-philosophy.md

Purpose:

Define how the ecosystem is structured.

---

## Phase 3 — Aaram Brain Core

Location:

```text
docs/02-brain-core/
```

Defines:

- Context Engine.
- Conversation Engine.
- Knowledge Engine.
- Decision Engine.
- Action Engine.
- AI Model Gateway.
- Memory Framework.

---

## Phase 4 — Intelligence Domains

Location:

```text
docs/03-intelligence-domains/
```

Defines:

- NDR Intelligence.
- Customer Query Intelligence.

---

## Phase 5 — Supporting Architecture

Includes:

- Data Models.
- Integrations.
- API Contracts.
- Events.
- Security.
- Governance.

---

# 11. Working Rules for AI Agents

All AI agents working on AaramBooks must follow:

## Rule 1

Do not jump into implementation before defining responsibility and ownership.

---

## Rule 2

Do not make technology decisions during architecture definition unless explicitly requested.

---

## Rule 3

Maintain separation between:

- Business Truth.
- Intelligence.
- Infrastructure.

---

## Rule 4

Do not create duplicate sources of truth.

---

## Rule 5

Respect existing domain ownership.

---

## Rule 6

If a discussion belongs to another documentation phase, redirect instead of mixing contexts.

---

# 12. Architecture Governance

Every major architectural decision should be:

- Clearly documented.
- Traceable.
- Reviewed against existing principles.

The architecture should evolve intentionally, not through accidental expansion.

---

# 13. Final Definition

AaramBooks is an AI-native business operating system where independent business systems maintain operational truth and Aaram Brain transforms that truth into intelligence, recommendations, automation, and improved business outcomes.

The foundational rule of the ecosystem is:

> Business systems create truth. Aaram Brain creates intelligence from that truth.
