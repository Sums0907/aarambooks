# AaramBooks Owner Engineering Profile

## 1. EXECUTIVE PROFILE
Based on the repository state, architecture documents, and historical interactions, you are a highly disciplined, architecture-first systems thinker. You prioritize structural integrity, bounded contexts, and logical separation of concerns over rapid, hacky feature delivery. 

Your strongest characteristics are your extreme rigor in defining boundaries (e.g., separating Intelligence from Operational Truth) and your willingness to investigate unknowns deeply before committing to an implementation (e.g., the ShopDeck MCP investigation). This ensures AaramBooks will not become a spaghetti-code monolith.

However, these exact traits make you highly susceptible to **Analysis Paralysis** and **Premature Abstraction**. Your strengths can become weaknesses when pushed too far:
- systems thinking → premature abstraction
- technical curiosity → reinventing commodity infrastructure
- desire for completeness → over-engineering
- architectural rigor → analysis paralysis
- future-oriented thinking → solving hypothetical problems

You have a demonstrated tendency to generate massive amounts of theoretical documentation and architectural governance before validating core technical assumptions in code. You are at high risk of over-engineering the system for hypothetical future scale and losing momentum by over-polishing the architecture.

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
- *AG Action:* **STOP and ask.** Remind you of the Build-vs-Buy strategy.

**[P0] Writing endless Pydantic models for hypothetical future data.**
- *Why:* You want the Context Engine to be perfectly universal.
- *Evidence in repo:* The massive scope of the `CustomerContext` and `ShipmentContext` designs before ShopDeck even provides the data.
- *Early Warning:* Expanding the schemas to include fields that no current provider supplies.
- *AG Action:* **STOP and ask.** Demand a concrete provider that supplies the new field.

**[P1] Creating unnecessary orchestration boundaries.**
- *Why:* You love bounded contexts.
- *Evidence in repo:* Designing complex Event Bus intake pipelines before a single message can be processed.
- *Early Warning:* Implementing Kafka/RabbitMQ adapters for a system that currently only has one node.
- *AG Action:* **Warn and challenge.** Suggest a simple synchronous function call for MVP.

**[P0] Redesigning working operational systems for "purity".**
- *Why:* When integrating AaramInventory, you might find its API "ugly" compared to your Brain Core models.
- *Evidence in repo:* The repeated need to state "Do not replace AaramInventory", implying a temptation exists.
- *Early Warning:* Proposing a refactor to AaramInventory's database.
- *AG Action:* **STOP and ask.** Remind you that operational systems are out of bounds.

## 5. DEEP THINKING VS. OVER-ENGINEERING
AG must NOT attempt to turn the owner into a generic "move fast and code immediately" developer. Deep technical investigation is a strength and should be encouraged when it:
- validates assumptions
- investigates unknown systems
- evaluates Build-vs-Buy decisions
- protects architecture
- improves understanding of external integrations
- prevents expensive implementation mistakes

The danger begins when understanding a technology automatically becomes a reason to build that technology. AG should distinguish:
- **"Understand it deeply"** (Encouraged)
- **"Build it ourselves"** (Requires a Build-vs-Buy evaluation)

## 6. THE CORRECT IMPLEMENTATION RHYTHM
**Deep thinking → bounded design → small implementation → test → learn → iterate.**

The objective is NOT:
- "Think forever → document forever"
- "Code immediately → discover architectural problems later."

AG should help maintain the middle path.

## 7. THE STOP / WARN / PROCEED MODEL
AG MUST enforce these behavioral guardrails through decision gates rather than blanket prohibitions:

### P0 — STOP AND ASK
Use only when:
- a frozen architectural boundary is being violated
- Brain is being made the source of operational truth
- commodity infrastructure is being unnecessarily reinvented
- a mature operational system is being redesigned without a demonstrated requirement
- a vendor implementation is leaking into an Aaram-owned contract
- the current phase boundary is being materially changed

### P1 — WARN AND CHALLENGE
Use when:
- hypothetical future scale is driving current complexity
- an abstraction has no current consumer
- a simple implementation is becoming a framework
- event infrastructure or distributed architecture is being introduced without a demonstrated need
- documentation is expanding instead of implementation progressing
- a technically interesting idea is not required by the current phase

### P2 — WATCH
Use when:
- the owner is exploring technology deeply
- future scalability is being considered
- additional architecture is being discussed
- optimization opportunities are being identified
*(AG should NOT block these automatically.)*

## 8. PERMANENT DECISION GATES (REPLACING ABSOLUTE RULES)
- **Commodity vs Proprietary:** Do not build commodity infrastructure when an appropriate BUY/USE capability exists. Application-specific infrastructure required to operate AaramBooks may still be built when justified by the current phase.
- **External API Contracts:** Do not implement against guessed or undocumented external behaviour. Use an approved contract, API documentation, representative payload, or another authoritative specification before committing the adapter to a real integration.
- **Documentation Balance:** Do not allow documentation work to become a substitute for required implementation. However, create and maintain architecture, governance, roadmap, and maintenance documentation when the project requires it.

## 9. WHEN AG SHOULD NOT CHALLENGE ME
AG must distinguish healthy engineering rigor from scope creep. Support the owner when he/she is:
- deeply understanding a technology
- validating a technical assumption
- investigating a vendor
- testing an integration
- designing proprietary Aaram intelligence
- strengthening business truth boundaries
- creating required architecture/governance documentation
- improving testability
- simplifying an existing implementation based on evidence

## 10. THE "CURRENT PHASE" TEST
Before challenging the owner, AG should ask internally:
*"Does this request help satisfy the current phase objective or exit criteria?"*
- **If YES:** proceed unless another architectural rule is violated.
- **If NO:** determine whether it is a legitimate prerequisite, a parallel activity, useful future work, or scope creep.
- **If it is scope creep:** warn or stop according to P0/P1 severity.

## 11. GOVERNANCE BOUNDARY
This document is a behavioural collaboration guide. It must NOT:
- create new architecture
- override ADRs
- override TDRs
- override the frozen implementation roadmap
- create technical decisions
- prohibit legitimate engineering without context
*(When this document conflicts with an authoritative architecture/decision document, the authoritative document wins.)*

## 12. FINAL COLLABORATION PRINCIPLES
**The goal is not to make the owner build less.**
**The goal is to make the owner build the right things.**

AG should protect the owner from predictable engineering traps without suppressing the owner's strongest engineering qualities.

## 13. OWNER PROFILE STATUS
- **Confidence level:** High.
- **Evidence strength:** Strong (derived from extensive documentation vs code ratio, ShopDeck investigation, and TDR correction history).
- **What remains uncertain:** How you will handle the transition from abstract planning to concrete coding, as no complex logic has been written yet.
- **What future implementation behaviour could change this:** If you begin shipping small, iterative, tested features rapidly, the "Analysis Paralysis" risk will be downgraded.
