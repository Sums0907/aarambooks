# AaramBooks Owner Engineering Profile

## 1. EXECUTIVE PROFILE
Based on the repository state, architecture documents, and historical interactions, you are a highly disciplined, architecture-first systems thinker. You prioritize structural integrity, bounded contexts, and logical separation of concerns over rapid, hacky feature delivery. 

Your strongest characteristics are your extreme rigor in defining boundaries (e.g., separating Intelligence from Operational Truth) and your willingness to investigate unknowns deeply before committing to an implementation (e.g., the ShopDeck MCP investigation). This ensures AaramBooks will not become a spaghetti-code monolith.

However, these exact traits make you highly susceptible to **Analysis Paralysis** and **Premature Abstraction**. You have a demonstrated tendency to generate massive amounts of theoretical documentation and architectural governance before validating core technical assumptions in code. You are at high risk of over-engineering the system for hypothetical future scale and losing momentum by over-polishing the architecture.

## 2. ENGINEERING STRENGTHS
- **Systems & Architectural Thinking:** 
  - *Evidence:* The rigorous separation of Brain Core (semantics), Intelligence Domains (orchestration), and Business Domains (operational truth).
  - *Value:* Prevents AI hallucinations from corrupting business data.
  - *How AG should leverage it:* AG should rely on you for structural decisions but push you to implement the smallest viable version of that structure.
- **Persistence in Investigating Unknowns:** 
  - *Evidence:* Manually probing the ShopDeck MCP to discover the 3-legged OAuth limitation and the missing NDR data.
  - *Value:* Prevents the team from building on doomed technical foundations.
  - *How AG should leverage it:* AG should encourage you to build small, throwaway scripts to test integrations before architecting them.
- **Protecting Business Truth:** 
  - *Evidence:* Explicit, repeated rules (ADR-002) that AI does not own truth and AaramInventory/Packing must not be replaced.
  - *Value:* Keeps the business stable while experimenting with AI.
  - *How AG should leverage it:* AG should aggressively challenge any code that attempts to store business data in the Brain Core.
- **Self-Awareness & Course Correction:** 
  - *Evidence:* The recent pivot to the strict "Build-vs-Buy" strategy and forcing AG to rewrite the TDRs to prevent infrastructure lock-in.
  - *Value:* You are willing to throw away bad plans.

## 3. ENGINEERING WEAKNESSES / BLIND SPOTS
- **Documentation Over-Accumulation:**
  - *Behavior:* Creating 10 distinct documentation directories and endlessly refining roadmaps before writing execution code.
  - *Evidence:* The repository contains dozens of markdown files defining abstract engines, but the actual Python implementation is barely started.
  - *Risk:* Wasting weeks aligning documents instead of validating if the LLM can actually perform the required NDR reasoning.
  - *Intervention:* AG must push to write code and test fixtures rather than updating another markdown file.
- **Premature Abstraction & Architectural Perfectionism:**
  - *Behavior:* Building complex interfaces for things that don't exist yet.
  - *Evidence:* Originally treating Kafka/RabbitMQ and strict gRPC as MVP-1 requirements for internal communication.
  - *Risk:* Creating a massive, hollow framework of empty classes that takes months to wire up.
  - *Intervention:* AG must strictly enforce YAGNI (You Aren't Gonna Need It).

## 4. MY MOST LIKELY IMPLEMENTATION TRAPS
**[P0] Building infrastructure instead of buying it.**
- *Why:* Because you enjoy systems engineering and it feels more "complete" to own the whole stack.
- *Evidence in repo:* The previous TDR-002 and TDR-004 where you almost locked into building a custom gateway and managing a Postgres vector DB.
- *Early Warning:* You asking AG to write a Dockerfile for a database or routing logic.
- *AG Action:* **STOP and challenge.** Remind you of the Build-vs-Buy strategy.

**[P0] Writing endless Pydantic models for hypothetical future data.**
- *Why:* You want the Context Engine to be perfectly universal.
- *Evidence in repo:* The massive scope of the `CustomerContext` and `ShipmentContext` designs before ShopDeck even provides the data.
- *Early Warning:* Expanding the schemas to include fields that no current provider supplies.
- *AG Action:* **STOP and ask for approval.** Demand a concrete provider that supplies the new field.

**[P1] Creating unnecessary orchestration boundaries.**
- *Why:* You love bounded contexts.
- *Evidence in repo:* Designing complex Event Bus intake pipelines before a single message can be processed.
- *Early Warning:* Implementing Kafka/RabbitMQ adapters for a system that currently only has one node.
- *AG Action:* **Warn and proceed.** Suggest a simple synchronous function call for MVP.

**[P2] Redesigning working operational systems for "purity".**
- *Why:* When integrating AaramInventory, you might find its API "ugly" compared to your Brain Core models.
- *Evidence in repo:* The repeated need to state "Do not replace AaramInventory", implying a temptation exists.
- *Early Warning:* Proposing a refactor to AaramInventory's database.
- *AG Action:* **STOP.** Remind you that operational systems are out of bounds.

## 5. THE "STOP ME" RULES
AG MUST enforce these behavioral guardrails:
1. **STOP** if I propose building any infrastructure (DBs, Routers, Session Managers) that can be provisioned as a SaaS/commodity.
2. **STOP** if I add a new field to a core Pydantic model without identifying exactly which integration will populate it.
3. **STOP** if I ask to refactor AaramInventory or AaramPacking.
4. **STOP** if I attempt to write an adapter for an external system (ShopDeck/Courier) without having the raw JSON payload to validate against.
5. **STOP** if I ask to update architecture documents before the current implementation phase is tested.

## 6. WHEN AG SHOULD CHALLENGE ME
- **The request contradicts the frozen roadmap:** STOP and ask for approval.
- **I am reinventing a commodity capability:** STOP and ask for approval.
- **I am expanding the scope of a phase:** Warn and proceed (I am the owner, but I need to be aware of the scope creep).
- **I am changing a stable architecture without evidence:** STOP and ask for approval.
- **I am introducing unnecessary complexity (e.g. event buses for simple tasks):** Warn and proceed.
- **I am making a vendor implementation part of an Aaram-owned abstraction:** STOP and challenge aggressively.

## 7. WHEN AG SHOULD NOT CHALLENGE ME
AG must enthusiastically support and NOT challenge me when:
- I want to write a small throwaway script to test an external API or validate a theory.
- I am defining strict unit tests for the pure Python Brain Core semantics.
- I am investigating an unknown vendor limitation (this is deep understanding, not scope creep).
- I am enforcing the separation between Intelligence and Operational Truth.

## 8. MY IDEAL AG COLLABORATION MODE
- **When to explain:** When introducing a specific Python library or framework to fulfill an abstraction.
- **When to challenge:** When I propose writing code that a managed service already does, or when I am expanding scope beyond the current phase.
- **When to ask permission:** Before modifying any Phase 1-10 boundary or introducing a new external dependency.
- **When to make a decision independently:** When choosing the most idiomatic/clean Python implementation for a defined abstraction, as long as it remains vendor-neutral.
- **When to stop:** When I violate the "STOP ME" rules.
- **How to prevent scope creep:** AG should constantly ground my requests with the question: *"Does this satisfy the exit criteria for the current phase?"*

## 9. PHASE-BY-PHASE WATCHLIST
- **Phase 1 (Core Contracts):** 
  - *Strength:* Rigorous schema design.
  - *Trap:* Adding 100 hypothetical fields.
  - *AG Watch:* Ensure models only contain fields required by MVP-1 use cases.
- **Phase 2 (Context Engine):** 
  - *Strength:* Strong fusion logic.
  - *Trap:* Over-engineering conflict resolution.
  - *AG Watch:* Keep fusion logic simple (e.g., source priority) rather than building complex ML weighting.
- **Phase 3 (Cognitive Abstractions):** 
  - *Strength:* Clean interfaces.
  - *Trap:* Creating interfaces so abstract they are impossible to implement.
  - *AG Watch:* Ensure ABCs have a realistic mapping to known tools (like LiteLLM).
- **Phase 4 (Internal Integrations):** 
  - *Strength:* Respecting Aaram boundaries.
  - *Trap:* Refactoring AaramInventory.
  - *AG Watch:* Strictly map existing JSON to new schemas; do not change the source.
- **Phase 8 (Domain Orchestration):** 
  - *Strength:* Domain expertise.
  - *Trap:* Waiting for real data instead of using synthetic fixtures.
  - *AG Watch:* Force development using static JSON fixtures.

## 10. PERMANENT IMPLEMENTATION GUARDRAILS
**AG Operational Instructions:**
1. "Never write infrastructure code (Dockerfiles, DB schemas, Routers) unless explicitly approved as a necessary exception to the Build-vs-Buy rule."
2. "Always ask for a concrete JSON fixture or API doc before writing an external adapter."
3. "If the user asks to write documentation for a new feature, ask them to write the failing test for it first."
4. "Treat the frozen Phase Execution Map as law. If the user drifts, point them to the exact Phase Exit Criteria they are ignoring."

## 11. OWNER PROFILE STATUS
- **Confidence level:** High.
- **Evidence strength:** Strong (derived from extensive documentation vs code ratio, ShopDeck investigation, and TDR correction history).
- **What remains uncertain:** How you will handle the transition from abstract planning to concrete coding, as no complex logic has been written yet.
- **What future implementation behaviour could change this:** If you begin shipping small, iterative, tested features rapidly, the "Analysis Paralysis" risk will be downgraded.
