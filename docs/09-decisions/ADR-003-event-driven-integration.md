# ADR-003: Event Driven Integration

## Status
Accepted

## Decision

AaramBooks ecosystem communication follows governed event-driven principles where business systems publish meaningful business changes and Aaram Brain consumes those signals for intelligence purposes.

Events represent business truth changes created by responsible systems.

## Architectural Intent

Event-driven communication preserves:
- Clear ownership boundaries.
- Loose ecosystem coupling.
- Traceable intelligence evolution.
- Controlled future expansion.

Events allow Aaram Brain capabilities to evolve without forcing business systems to transfer ownership.

## Governance Principle

Events communicate truth changes.

They do not redefine ownership.

Business systems remain authoritative sources of truth.
