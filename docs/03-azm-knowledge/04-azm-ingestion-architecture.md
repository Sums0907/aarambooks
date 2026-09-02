# Azm Ingestion Architecture

**Document Reference:** `docs/03-azm-knowledge/04-azm-ingestion-architecture.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Logical Ingestion Lifecycle

The critical distinction in this architecture is the difference between "reading a contract" and "building AZM knowledge from the contract". Azm is NOT a contract repository. The contract is source material. AZM's persistent knowledge is the independently modeled, provenance-tagged result.

The lifecycle is defined strictly as follows:

1. **Business System Ownership:** The Business System (e.g., Catalog BS) finalizes its internal operational truth.
2. **Contract Publication:** The BS publishes EXACTLY TWO governed contracts: the Semantic Public Contract (meaning) and the Schematic Public Contract (exposure).
3. **Azm Ingestion Trigger:** Azm detects a new or updated contract version.
4. **Interpretation & Normalization:** Azm maps the raw BS declarations into Azm's normalized logical primitives (Semantic Concepts, Schematic References, Schematic Attributes).
5. **Source-Declared Knowledge Persistence:** Azm commits every directly stated declaration as a Source-Declared knowledge node, tagged with full provenance tracing to the specific BS, contract, version, and declaration element.
6. **AZM-Derived Knowledge Construction:** Azm infers connective tissue by recognizing relationships across BS contracts. These are persisted as AZM-Derived knowledge nodes with derivation provenance that explicitly records which source contracts and which reasoning method produced the relationship. **AZM-Derived knowledge must be clearly distinguished from Source-Declared knowledge in the persistent store.**
7. **Provenance Tagging:** Every generated primitive is tagged with exact lineage (BS → Contract ID → Declaration Element → Ingestion Run). Azm generates its *own* Knowledge Identity (UUID), distinct from any Business System operational UUID.
8. **Validation:** Azm verifies the new knowledge against global invariants (e.g., no `EXTERNAL_CHANNEL` concept may overwrite an `AARAM_NATIVE` concept).
9. **Persistence:** Azm commits the normalized knowledge to its persistent database.
10. **Knowledge Availability:** Brain Core queries the active knowledge.

---

## 2. Source-Declared vs. AZM-Derived Knowledge

This distinction is fundamental to Azm's integrity.

| Knowledge Kind | Definition | Provenance |
|---|---|---|
| **Source-Declared** | Explicitly stated in a BS Public Contract and faithfully normalized into AZM. | Traces to: BS → Contract → Version → Declaration Element |
| **AZM-Derived** | Inferred by AZM from relationships across two or more BS contracts. No single BS stated this relationship. | Traces to: [BS-A Contract + BS-B Contract] → Derivation Method → Ingestion Run |

A derived cross-BS relationship must be able to answer:
> *"Why does AZM believe that `catalog.sku` has `inventory.stock_balance`?"*
> Answer: *"AZM derived this relationship during ingestion run #42, by recognizing that both Catalog BS (Semantic Contract v1) and Inventory BS (Semantic Contract v1) declare concepts in the same physical domain (product commerce), and that their schematic surfaces are designed to be joined on `sku_id`."*

AZM must never silently invent a derived relationship without recordable justification.

---

## 3. Handling Knowledge Evolution

### 3.1 New Concepts
Azm creates a new `Semantic Concept` node, tags it with provenance, and activates it.

### 3.2 Changed Concepts & Versioning
Azm tracks evolution securely. If a definition changes, Azm creates a new knowledge version. If a field is renamed in the Schematic Contract, Azm updates the `Attribute Mapping` and creates a new version of the affected `Schematic Attribute`, deprecating the old one. Historical knowledge is preserved, never silently overwritten.

### 3.3 Removed / Deprecated Concepts
If a concept is removed from a BS Public Contract, Azm marks the knowledge node as `DEPRECATED` or `INACTIVE`.

### 3.4 External / Channel Mappings
If a contract contains external channel mappings (e.g., ShopDeck's `customer_sku_short_id`), Azm creates an `External Mapping` node linked to the canonical `AARAM_NATIVE` `Semantic Concept`. The external mapping is never elevated to canonical status.

### 3.5 Conflicting Source Declarations
**OPEN GAP / DECISION REQUIRED:** The exact conflict resolution protocol when two Business Systems legitimately differ in their declaration of a shared boundary concept is not yet formally established. Currently, ingestion validation flags this as a Boundary Conflict Error requiring human review.

### 3.6 Re-ingestion and Stale Knowledge
Azm maintains a hash of the source contracts. If a contract changes out-of-band, the ingestion engine detects the delta, archives the old knowledge version, and persists the new version.

---

## 4. What Ingestion Produces

After a successful ingestion run, AZM must have produced:

| Contract Ingested | AZM Knowledge Produced |
|---|---|
| BS Semantic Public Contract | Semantic Concept nodes (one per declared concept), with definitions, aliases, provenance |
| BS Schematic Public Contract | Schematic Reference nodes (one per view/API), Schematic Attribute nodes (one per field), Attribute Mapping nodes linking fields to concepts |
| Both contracts combined | AZM-Derived Semantic Relationship nodes (cross-concept relationships), External/Channel Mapping nodes if applicable |

Ingestion does NOT produce: copies of the source contract files, operational data records, or BS-internal table definitions.
