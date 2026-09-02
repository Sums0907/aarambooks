# Azm Knowledge Rules & Invariants

**Document Reference:** `docs/03-azm-knowledge/03-azm-knowledge-rules.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Operational Non-Interference
- **Azm NEVER owns Business System operational truth.** It does not process transactions or enforce operational business rules.
- **Azm NEVER becomes a second Business System.** It is strictly a knowledge repository.
- **Azm NEVER invents authoritative operational facts.** If a fact is not derivable from a governed Public Contract, Azm cannot claim it as truth.
- **Azm is NOT the semantic authority.** Business Systems declare authoritative domain meaning through their Semantic Public Contracts. AZM persists a normalized, queryable representation of that declared knowledge. AZM may not independently redefine, override, or contradict BS-declared meaning. The distinction is: SOURCE AUTHORITY (Business System) ≠ KNOWLEDGE REPRESENTATION (AZM).

## 2. The Contract Derivation Invariant
- **Azm is NOT a contract archive or markdown repository.**
- **Azm DOES NOT blindly mirror individual Business Systems.** It builds a unified cross-BS ecosystem ontology.
- **Business System Public Contracts are governed source material.** Azm reads this material, normalizes the declared knowledge, and derives its own persistent knowledge representation.
- **AZM performs limited, governed knowledge derivation at ingestion time ONLY.** It may infer cross-BS relationships from multiple governed contracts. It does NOT perform runtime reasoning — runtime reasoning is exclusively Brain Core's role.
- **The clean AZM boundary:** `Contracts → AZM Ingestion → Normalization → Governed Knowledge Derivation → Persistent AZM Knowledge DB`. Everything after that DB boundary (reasoning, orchestration) belongs to Brain Core.

## 3. The Brain Consumption Invariant
- **Brain Core NEVER directly consumes Business System Public Contracts.** The path from BS Contract to Brain is strictly forbidden to prevent bypassing Azm. Brain must not parse markdown or reverse-engineer DDL at runtime.
- **Brain Core consumes AZM knowledge.** It relies exclusively on Azm's normalized, versioned knowledge representation.
- **Intelligence Domains consume knowledge through the architecture.** They do not directly read BS contracts, inspect DDL, or bypass Azm to reconstruct semantics. An Intelligence Domain that reads BS contracts directly to understand meaning has become a shadow semantic system.

## 4. The Sovereignty of Aaram Semantics
- **External channels CANNOT redefine Aaram-native concepts.** ShopDeck channel definitions are explicitly classified as external mappings. They never overwrite the core Aaram ontology.
- **Provenance must distinguish Aaram-native meaning from external/channel meaning.** 

## 5. Knowledge Lifecycle & Versioning
- **Stale/changed source knowledge must be detectable.** Azm must track source contract hashes to version knowledge securely.
- **Historical knowledge is not silently overwritten.** New ingestion creates new versions.
- **Active vs Historical:** Brain normally queries active knowledge unless historical context is explicitly requested.
