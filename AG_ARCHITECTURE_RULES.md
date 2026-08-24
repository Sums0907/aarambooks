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
