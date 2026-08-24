# AG Workflow — AaramBooks AI Agent Operating Workflow

## Purpose

Define the mandatory workflow for AI agents working on AaramBooks architecture and implementation tasks.

The objective is to ensure every change remains synchronized with the repository source of truth and follows architecture governance.

---

# Repository Synchronization Rule

Before starting any module task, AI agents must synchronize context from the repository.

Mandatory reads:

1. AG_MASTER_CONTEXT.md
2. AG_ARCHITECTURE_RULES.md
3. AG_DO_NOT_DO.md
4. AG_TERMINOLOGY.md
5. AG_CONTEXT_SYNC.md (if available)
6. Relevant module documentation

Previous chat history must not be treated as architectural truth.

---

# GitHub Commit Rule

Every new file created by an AI agent must be committed to GitHub.

Every existing file modified by an AI agent must be committed to GitHub.

No completed architecture work should exist only in chat output.

The repository is the authoritative record of architecture evolution.

---

# Documentation Workflow

The mandatory workflow is:

Repository Context Sync

↓

Read Relevant Architecture Documents

↓

Analyze Ownership Boundaries

↓

Create or Update Documentation

↓

Validate Against Architecture Rules

↓

Commit Changes to GitHub

↓

Report Commit Summary

---

# Architecture Change Governance

AI agents must not silently modify architecture outside the assigned module boundary.

If a change impacts:

- Brain Core
- Business Domains
- Intelligence Domains
- ADR decisions

The agent must:

1. Document the impact.
2. Identify affected boundaries.
3. Raise an architecture decision requirement.
4. Wait for approved governance resolution.

---

# Completion Requirement

A module task is complete only when:

- Documentation is created or updated.
- Validation is performed.
- Required changes are committed to GitHub.
- Repository context remains consistent.

---

# Core Principle

Business systems create truth.

Aaram Brain creates intelligence from that truth.
