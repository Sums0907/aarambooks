# Azm Knowledge Rules & Invariants

**Document Reference:** `docs/03-azm-knowledge/03-azm-knowledge-rules.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Operational Non-Interference
- **Azm NEVER owns Business System operational truth.** It does not process transactions, validate state changes, or enforce operational business rules.
- **Azm NEVER becomes a second Business System.** It is strictly a knowledge repository.
- **Azm NEVER invents authoritative operational facts.** If a fact is not derivable from a governed Public Contract, Azm cannot claim it as truth.

## 2. The Contract Derivation Invariant
- **Azm is NOT a contract archive.** It does not simply store copies of markdown files or SQL DDL scripts.
- **Azm DOES NOT blindly mirror contracts.**
- **Business System Public Contracts are governed source material.** Azm reads this material, extracts the meaning, and *derives* its own persistent knowledge representation (Concepts, Schemas, Relationships).

## 3. The Brain Consumption Invariant
- **Brain Core NEVER directly consumes Business System Public Contracts.** The path from BS Contract to Brain is strictly forbidden.
- **Brain Core consumes AZM knowledge.** It relies on Azm's derived representation of the contracts.
- **Intelligence Domains consume knowledge through the architecture.** They do not bypass Azm to become shadow semantic masters.

## 4. The Sovereignty of Aaram Semantics
- **External channels CANNOT redefine Aaram-native concepts.** ShopDeck, Amazon, or Flipkart channel definitions are explicitly classified as external mappings. They never overwrite the core Aaram ontology.
- **Provenance must distinguish Aaram-native meaning from external/channel meaning.** The knowledge model must clearly flag whether a concept is canonical (Aaram) or external (ShopDeck).

## 5. Knowledge Lifecycle & Detectability
- **Stale/changed source knowledge must be detectable.** When a Business System updates its Public Contract, Azm must be able to detect the delta, version the knowledge, and update its persistent state safely.
