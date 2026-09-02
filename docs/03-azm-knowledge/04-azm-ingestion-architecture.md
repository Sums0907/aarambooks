# Azm Ingestion Architecture

**Document Reference:** `docs/03-azm-knowledge/04-azm-ingestion-architecture.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Logical Ingestion Lifecycle

The critical distinction in this architecture is the difference between "reading a contract" and "building AZM knowledge from the contract". Azm is NOT a contract repository.

The lifecycle is defined strictly as follows:

1. **Business System Ownership:** The Business System (e.g., Catalog BS) finalizes its internal operational truth.
2. **Contract Publication:** The BS publishes EXACTLY TWO governed contracts: the Semantic Public Contract (meaning) and the Schematic Public Contract (exposure).
3. **Azm Ingestion Trigger:** Azm detects a new or updated contract version.
4. **Interpretation & Normalization:** Azm maps the raw BS declarations into Azm's normalized logical primitives.
5. **Knowledge Derivation:** Azm infers connective tissue, building cross-BS relationships.
6. **Provenance Tagging:** Azm tags every generated primitive with exact lineage (BS -> Contract ID -> Declaration Element -> Ingestion Run). Azm generates its *own* Knowledge Identity, distinct from Source Identity.
7. **Validation:** Azm verifies the new knowledge against global invariants.
8. **Persistence:** Azm commits the normalized knowledge to its persistent database.
9. **Knowledge Availability:** Brain Core queries the active knowledge.

---

## 2. Handling Knowledge Evolution

### 2.1 New Concepts
Azm creates a new `Semantic Concept` node, tags it with provenance, and activates it.

### 2.2 Changed Concepts & Versioning
Azm tracks evolution securely. If a definition changes, Azm creates a new knowledge version. If a field is renamed in the Schematic Contract, Azm updates the `Attribute Mapping`, deprecating the old mapping. Historical knowledge is preserved, never silently overwritten.

### 2.3 Removed / Deprecated Concepts
If a concept is removed from a BS Public Contract, Azm marks the knowledge node as `DEPRECATED` or `INACTIVE`.

### 2.4 External / Channel Mappings
If a contract contains external channel mappings (e.g., ShopDeck's `customer_sku_short_id`), Azm creates an `External Mapping` node linked to the canonical `Semantic Concept`.

### 2.5 Conflicting Source Declarations
**OPEN GAP / DECISION REQUIRED:** The exact conflict resolution protocol when two Business Systems legitimately differ in their declaration of a shared boundary concept is not yet formally established. Currently, ingestion validation flags this as a Boundary Conflict Error.

### 2.6 Re-ingestion and Stale Knowledge
Azm maintains a hash of the source contracts. If a contract changes out-of-band, the ingestion engine detects the delta, archives the old state, and persists the new version.
