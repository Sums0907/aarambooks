# AaramBooks AI Context Synchronization Protocol

## Purpose

Ensure all AI agents working on AaramBooks operate with the same architectural understanding.

---

# Source of Truth

The GitHub repository documentation is the authoritative context source.

AI agents must not rely on previous chat history as architectural truth.

---

# Session Initialization

At the beginning of every module conversation:

Read:

1. AG_MASTER_CONTEXT.md
2. AG_ARCHITECTURE_RULES.md
3. AG_DO_NOT_DO.md
4. AG_TERMINOLOGY.md
5. Module-specific documentation

---

# Module Isolation Rule

Each AI session works within a defined module boundary.

Examples:

API Contracts Chat:
- Reads API documentation.
- Does not redesign Brain Core.

NDR Chat:
- Reads NDR documentation.
- Does not redefine integrations.

---

# Cross-Module Discovery Rule

If a module discovers a requirement affecting another module:

The AI must:

1. Document the discovery.
2. Identify affected boundaries.
3. Raise an architecture decision request.

The AI must not:

- Modify another module silently.
- Expand responsibilities.
- Change ADR decisions.

---

# Architecture Decision Flow

Discovery

↓

Architecture Review

↓

Decision

↓

Update Documents

↓

Continue Implementation

---

# Completion Synchronization

After completing a module:

Update:

- Module documentation.
- Relevant ADRs if required.
- AG_CURRENT_TASK.md if workflow changes.
