# AaramBooks Project Phases

## Purpose

This document defines the development methodology and current execution phase of the AaramBooks architecture project.

All AI agents working on AaramBooks must understand the current phase before creating or modifying documents.

---

# Phase 0 — Context Foundation

Status: COMPLETED

Purpose:

Create a persistent AI-readable project context.

Created:

- AG_MASTER_CONTEXT.md
- AG_ARCHITECTURE_RULES.md
- AG_CONTEXT_SYNC.md
- AG_CURRENT_TASK.md
- AG_DO_NOT_DO.md
- AG_TERMINOLOGY.md

Outcome:

AI agents can rebuild project understanding from GitHub documentation.

---

# Phase 1 — Architecture Design

Status: COMPLETED

Purpose:

Define what AaramBooks is and establish ownership boundaries.

Completed:

- AaramBooks ecosystem architecture.
- Business domain boundaries.
- Aaram Brain architecture.
- Brain Core design.
- Intelligence Domain design.

Completed Intelligence Domains:

- NDR Intelligence.
- Customer Query Intelligence.

Governance completed:

- ADRs.
- Open Decisions Register.

Outcome:

Architecture foundation is frozen.

---

# Phase 2 — Contract Design

Status: IN PROGRESS

Purpose:

Define how systems communicate without violating ownership boundaries.

Focus:

- API Contracts.
- Event Contracts.

Principles:

- Contracts define communication.
- Contracts do not transfer ownership.
- Business systems remain truth owners.
- Aaram Brain provides intelligence.

Current task:

Create API contracts.

First document:

docs/06-api-contracts/brain-core-api-contracts.md

---

# Phase 3 — Data Model Design

Status: NOT STARTED

Purpose:

Define conceptual data ownership and structures.

Focus:

- Intelligence entities.
- Context models.
- Memory models.
- Event payload structures.

Rules:

Do not duplicate operational truth.

---

# Phase 4 — Integration Design

Status: NOT STARTED

Purpose:

Define interaction with external and operational systems.

Focus:

- ShopDeck.
- Logistics.
- Communication channels.
- AI providers.

---

# Phase 5 — Implementation Planning

Status: NOT STARTED

Purpose:

Convert architecture into executable development sequence.

Focus:

- Build order.
- Dependencies.
- Testing strategy.
- Deployment approach.

---

# Phase 6 — Development

Status: FUTURE

Purpose:

Implement approved architecture.

At this stage:

- AG becomes primary implementation assistant.
- Code changes begin.
- Tests and deployment are created.

---

# Phase 7 — Validation and Evolution

Status: FUTURE

Purpose:

Improve intelligence based on real operational outcomes.

Focus:

- AI evaluation.
- Business metrics.
- Continuous improvement.

---

# Phase Transition Rule

A phase should not start until the previous phase has produced sufficient documentation.

Architecture decisions must exist before implementation.

Contracts must exist before integration development.

Data ownership must exist before database design.

---

# Current Project Position

Current phase:

Phase 2 — Contract Design

Current active module:

06-api-contracts

Next planned modules:

07-events
08-security-governance refinement
04-data-models refinement
05-integrations
10-implementation-plan
