# AaramBooks Architecture Baseline

## Purpose

The purpose of the AaramBooks architecture is to establish a clear, governed ecosystem separating operational business truth from intelligence capabilities. This baseline document serves as the foundational architectural contract for AaramBooks.

## Approved Status

Modules 00 through 10 have been audited and hold an **approved status**. These modules establish the foundational architecture, domain boundaries, API contracts, event architecture, and implementation planning frameworks.

## Architecture Hierarchy

1. **Intelligence Applications**: Deliver business experiences (e.g., NDR Intelligence, Customer Query Intelligence).
2. **Aaram Brain Core**: Provides foundational, reusable intelligence capabilities (Context, Knowledge, Reasoning, Decision, Action).
3. **Business Domain Systems**: Maintain operational truth and business execution (e.g., AaramIdentity, AaramInventory, AaramPacking).

## Ownership Boundaries

- **Business Domain Systems** own their respective operational truth and business records.
- **Aaram Brain** owns the intelligence capabilities built upon that truth.
- Ownership of truth cannot be transferred through integrations, API contracts, or events.

## Governing Principle

> Business systems create truth.
> Aaram Brain creates intelligence from that truth.

---

## Future AI Agent Instructions

Before modifying any aspect of the AaramBooks architecture, future AI agents **must** adhere to the following governance rules:

1. **Read `architecture-baseline.md`** (this document) to understand the foundational principles and ownership model.
2. **Read referenced modules** relevant to the task (e.g., Module 01-10) to understand the established architectural decisions.
3. **Preserve ownership boundaries**. Do not allow Aaram Brain to become an operational system or duplicate business truth.
4. **Do not redesign approved modules**. Follow the established guidelines for expanding intelligence domains and integrating capabilities without violating the established architecture.
