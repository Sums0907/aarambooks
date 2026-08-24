# ADR-001: Brain Separation

## Status
Accepted

## Decision

AaramBooks maintains a strict separation between business systems and Aaram Brain.

Business systems remain responsible for creating, maintaining, and owning operational truth within their respective domains.

Aaram Brain consumes trusted information from business systems and creates intelligence, reasoning, recommendations, and actions within governed boundaries.

Aaram Brain must not become a replacement for operational systems or a duplicate owner of business truth.

## Architectural Intent

This decision preserves the foundational ecosystem boundary:

Business Systems:
- Own domain responsibility.
- Create operational truth.
- Maintain business authority.

Aaram Brain:
- Understands trusted information.
- Creates intelligence.
- Supports responsible decisions.

This separation allows intelligence capabilities to evolve without creating ownership conflicts.

## Governance Principle

Future architecture decisions must preserve:

Business systems create truth.

Aaram Brain creates intelligence from that truth.
