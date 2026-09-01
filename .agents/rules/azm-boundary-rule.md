---
name: Enforce AZM Separation of Concerns
description: Ensures agents always respect the Azm layer and never mix semantic knowledge into Intelligence Domains.
---

# CRITICAL SYSTEM BOUNDARY: AZM (Aaram Zameer)

You are working in the AaramBooks ecosystem, which uses a strict 4-Box Architecture. 

## The Rule
When building, refactoring, or modifying any **Intelligence Domain (ID)**, you **MUST NOT** invent, hardcode, or store semantic knowledge or schema definitions inside the ID. 

**AZM** is the global, ecosystem-wide repository of semantic and schematic knowledge.
- **WHAT** a concept means lives in AZM (`src/azm/`).
- **WHAT** schema exposes it lives in AZM (`src/azm/`).
- **HOW** to resolve the user's intent is Brain Core.
- **WHAT** it means for a business objective is the Intelligence Domain.

## Your Obligation
Every single time you work on an Intelligence Domain (e.g., Catalog ID, NDR ID, Inventory ID), you must first check if the necessary semantic concepts and Public Read Contract schemas exist in the `src/azm/namespaces/` directory. If they do not, you must build them in AZM, **not** in the ID. 

Azm means "resolve" or "determination". It is the emotional and architectural soul of the project's knowledge. Never bypass it.
