# SABAQ: Intelligence Training & Prior Data (ITPD)

## Purpose

SABAQ is the generic Aaram Intelligence Substrate. Its purpose is to provide Intelligence Domains (Catalog, NDR, Customer Query) with retrievable prior evidence and accumulated experience. It acts as an **advisory prior-data/experience layer** to drastically improve reasoning quality without hallucination.

**SABAQ IS NOT "LLM TRAINING".**
It does not fine-tune weights or build training pipelines. It provides *Intelligence Training & Prior Data* via retrieval, supplying exact historical business facts to the LLM (inference component) as context.

## Architectural Boundaries

1. **Domain-Neutral Infrastructure:** SABAQ is partitioned strictly by Intelligence Domain namespaces.
2. **Independent of AZM:** AZM remains the authority for semantic and schematic definitions. SABAQ stores examples, not schemas.
3. **Independent of MemoryProvider:** MemoryProvider handles short-term active conversational session state. SABAQ handles long-term historical examples and verified outcomes.
4. **Advisory Only:** SABAQ provides context. It is *never* an operational source of truth.
5. **Business System Validation:** SABAQ never bypasses CEM or Business System validation.
6. **No AI Guessing:** SABAQ enforces a strict `SabaqProvenance` model (`BUSINESS_SYSTEM_HISTORY`, `HUMAN_APPROVED_DECISION`, `DERIVED_PROFILE`). It is explicitly forbidden from persisting unapproved AI guesses.

## Core Terminology

- **SabaqProvider**: The domain-neutral interface for retrieving and recording experience.
- **SabaqEvidence**: A single verified piece of prior data/experience.
- **SabaqProvenance**: The authoritative classification of where the evidence came from, ensuring AI guesses are never durably stored.
