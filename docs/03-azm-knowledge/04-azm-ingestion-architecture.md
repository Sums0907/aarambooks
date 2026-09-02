# Azm Ingestion Architecture

**Document Reference:** `docs/03-azm-knowledge/04-azm-ingestion-architecture.md`
**System Name:** Aaram Zameer (`Azm`)
**Classification:** Foundational Architecture

---

## 1. The Logical Ingestion Lifecycle

The critical distinction in this architecture is the difference between "reading a contract" and "building AZM knowledge from the contract".

The lifecycle is defined strictly as follows:

1. **Business System Ownership:** The Business System (e.g., Catalog BS) finalizes its internal operational truth.
2. **Contract Publication:** The BS publishes a governed Semantic Public Contract (what things mean) and a Schematic Public Contract (how to query them via SQL/API).
3. **Azm Ingestion Trigger:** Azm detects (or is triggered to process) a new or updated contract version.
4. **Interpretation & Normalization:** Azm parses the contract text/schema. It maps the raw BS declarations into Azm's normalized logical primitives (Concepts, Relationships, Schema References).
5. **Knowledge Derivation:** Azm infers necessary connective tissue (e.g., linking a new Semantic Concept to an existing Domain).
6. **Provenance Tagging:** Azm tags every generated primitive with the source contract ID, version, and timestamp.
7. **Validation:** Azm verifies the new knowledge does not violate global invariants (e.g., a channel concept trying to overwrite an Aaram-native concept).
8. **Persistence:** Azm commits the normalized knowledge to its persistent database.
9. **Knowledge Availability:** Brain Core can now query the active knowledge.

---

## 2. Handling Knowledge Evolution

Azm must dynamically handle the reality of evolving Business Systems.

### 2.1 New Concepts
When a BS declares a new concept, Azm creates a new `Semantic Concept` node, tags it with provenance, and activates it.

### 2.2 Changed Concepts & Renamed Fields
Azm uses the combination of `Namespace` + `Concept Identity` to track evolution. If a definition changes, Azm creates a new knowledge version. If a field is renamed in the Schematic Contract, Azm updates the `Attribute Mapping`, deprecating the old mapping.

### 2.3 Removed / Deprecated Concepts
If a concept is removed from a BS Public Contract, Azm **DOES NOT** delete it from the persistent database. It marks the knowledge node as `DEPRECATED` or `INACTIVE`, ensuring historical reasoning by Brain Core remains intact for older data.

### 2.4 External / Channel Mappings
If a contract contains external channel mappings (e.g., ShopDeck's `customer_sku_short_id`), Azm strictly isolates this. It creates an `External Mapping` node linked to the canonical `Semantic Concept`. It never replaces the canonical definition.

### 2.5 Conflicting Source Declarations
If two Business Systems attempt to define the exact same core concept (e.g., both Inventory and Catalog trying to own the definition of a SKU), Azm's ingestion validation will throw a `Boundary Conflict Error`. Azm enforces single-source-of-truth ownership.

### 2.6 Re-ingestion and Stale Knowledge
Azm maintains a hash or version manifest of the source contracts it has ingested. If a contract changes out-of-band (stale knowledge), Azm's ingestion engine detects the delta on the next sync, archives the old state, and persists the new state.
