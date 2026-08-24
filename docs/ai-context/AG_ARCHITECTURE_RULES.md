# AG Architecture Rules

## Truth Ownership

1. Every business capability must have a clear owner.
2. Do not create duplicate sources of operational truth.
3. Aaram Brain consumes business truth; it does not own it.

## Domain Boundaries

1. Business domains evolve independently.
2. Do not directly couple unrelated domains.
3. Do not access another domain's internal implementation.

## Integration

1. Use approved APIs and event contracts.
2. Respect integration ownership.
3. Preserve domain boundaries.

## Brain Rules

1. Brain Core must remain generic.
2. Intelligence Domains contain business-specific intelligence.
3. Do not mix business workflows into Brain Core.

## Implementation Discipline

Before coding:
- Read relevant architecture documents.
- Confirm ownership.
- Confirm data model.
- Confirm API/event contract.

Do not implement based only on assumptions.

---

# Cross-Module Change Governance

## Architectural Impact Escalation Rule

AaramBooks follows a controlled architecture evolution process.

Individual modules and domains may identify:

- Missing capabilities.
- Design conflicts.
- Integration requirements.
- New dependencies.
- Architectural risks.

However, a module must not independently modify or redefine another module's architecture.

---

## Module Boundary Rule

A module owns only its approved responsibility.

Examples:

- NDR Intelligence may refine NDR workflows.
- Customer Query Intelligence may refine customer interaction intelligence.
- API Contracts may define communication boundaries.

A module must not silently change:

- Brain Core responsibilities.
- Business Domain ownership.
- Another Intelligence Domain behavior.
- Architecture principles.
- ADR decisions.

---

## Architecture Escalation Process

When a module discovers a requirement affecting another module:

1. Document the discovered requirement.
2. Identify the affected architecture boundary.
3. Create an architecture decision request.
4. Resolve the decision at the architecture governance layer.
5. Update impacted documents after approval.

The discovery module must not directly implement cross-module architectural changes.

---

## Example

Incorrect:

API Contracts discovers:

"Action Engine requires approval workflow."

API Contracts modifies Brain Core design directly.

Correct:

API Contracts identifies:

"Action Engine approval workflow requirement."

↓

Architecture decision review.

↓

Brain Core architecture updated if approved.

↓

API Contracts updated accordingly.

---

## Principle

Local optimization must never override ecosystem architecture consistency.

AaramBooks evolves through controlled architectural decisions, not isolated module changes.
