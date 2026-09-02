# Azm Knowledge Rules & Invariants

**Document Reference:** `docs/03-azm-knowledge/03-azm-knowledge-rules.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. Operational Non-Interference
- **Azm NEVER owns Business System operational truth.** It does not process transactions or enforce operational business rules.
- **Azm NEVER becomes a second Business System.** It is strictly a knowledge repository.
- **Azm NEVER invents authoritative operational facts.** If a fact is not derivable from a governed Public Contract, Azm cannot claim it as truth.

## 2. The Contract Derivation Invariant
- **Azm is NOT a contract archive or markdown repository.**
- **Azm DOES NOT blindly mirror individual Business Systems.** It builds a unified cross-BS ecosystem ontology.
- **Business System Public Contracts are governed source material.** Azm reads this material, extracts meaning, and *derives* its own persistent knowledge representation.

## 3. The Brain Consumption Invariant
- **Brain Core NEVER directly consumes Business System Public Contracts.** The path from BS Contract to Brain is strictly forbidden to prevent bypassing Azm. Brain must not parse markdown or reverse-engineer DDL at runtime.
- **Brain Core consumes AZM knowledge.** It relies exclusively on Azm's derived representation of the contracts.
- **Intelligence Domains consume knowledge through the architecture.** They do not bypass Azm to become shadow semantic masters.

## 4. The Sovereignty of Aaram Semantics
- **External channels CANNOT redefine Aaram-native concepts.** ShopDeck channel definitions are explicitly classified as external mappings. They never overwrite the core Aaram ontology.
- **Provenance must distinguish Aaram-native meaning from external/channel meaning.** 

## 5. Knowledge Lifecycle & Versioning
- **Stale/changed source knowledge must be detectable.** Azm must track source contract hashes to version knowledge securely.
- **Historical knowledge is not silently overwritten.** New ingestion creates new versions.
- **Active vs Historical:** Brain normally queries active knowledge unless historical context is explicitly requested.
