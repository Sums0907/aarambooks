---
description: Critical execution guardrails to protect against over-engineering and infrastructure scope creep during AaramBooks implementation.
---

# Owner Engineering Guardrails

The system owner has explicitly commanded that these guardrails be enforced by AG during all implementation phases. 

## 1. Build-vs-Buy Enforcement
Never write infrastructure code (Dockerfiles, DB schemas, custom Routers, custom Event Buses) unless explicitly approved as a necessary exception to the Build-vs-Buy rule. If the user proposes building commodity infrastructure that can reasonably be bought/used as a SaaS, **STOP and challenge them.**

## 2. Abstraction Guardrails
Do not add hypothetical fields to core Pydantic models. Always ask for a concrete JSON fixture or API doc before writing an external adapter or extending a schema. If the user introduces an abstraction without a current concrete consumer, **STOP and ask for approval.**

## 3. Boundary Protection
AaramInventory and AaramPacking are out-of-bounds operational systems. If the user asks to refactor or change a mature operational system without a demonstrated requirement, **STOP and challenge.** Do not make a vendor implementation part of an Aaram-owned abstraction.

## 4. Phase Governance
Treat the frozen Phase Execution Map (`docs/10-implementation-plan/implementation-backlog.md`) as law. If the user expands the scope of the current phase or tries to solve a hypothetical scale problem without evidence, point them to the exact Phase Exit Criteria they are ignoring.

## 5. Development Velocity
If the user asks to write extensive architectural documentation for a new feature, ask them to write the failing test or implementation for it first. Enforce YAGNI (You Aren't Gonna Need It).

**Reference Profile:** `docs/10-implementation-plan/owner-engineering-profile.md`
