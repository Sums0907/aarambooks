-- =============================================================================
-- AZM (Aaram Zameer) — Persistent Knowledge Database Schema
-- Version: 1.0
-- =============================================================================
-- Design principles:
--   - TEXT PRIMARY KEY for all UUIDs (SQLite-compatible, Postgres-compatible)
--   - knowledge_kind: SOURCE_DECLARED | AZM_DERIVED (on every knowledge table)
--   - lifecycle: ACTIVE | DEPRECATED | ARCHIVED (on every knowledge table)
--   - Every knowledge assertion references azm_provenance
--   - AZM generates its own UUIDs — never reuses Business System PKs
--   - No operational business records stored here
-- =============================================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ---------------------------------------------------------------------------
-- 1. azm_namespaces
--    Domain boundary of knowledge ownership (e.g. 'catalog', 'inventory').
--    classification: AARAM_NATIVE (from Aaram BS) | EXTERNAL_CHANNEL (e.g. ShopDeck)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_namespaces (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    classification  TEXT NOT NULL
                        CHECK (classification IN ('AARAM_NATIVE', 'EXTERNAL_CHANNEL')),
    description     TEXT,
    lifecycle       TEXT NOT NULL DEFAULT 'ACTIVE'
                        CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    created_at      TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 2. azm_ingestion_runs
--    Log of each ingestion attempt. Used for idempotency (hash-based).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_ingestion_runs (
    id               TEXT PRIMARY KEY,
    source_bs        TEXT NOT NULL,
    contract_type    TEXT NOT NULL
                         CHECK (contract_type IN ('SEMANTIC', 'SCHEMATIC', 'FULL', 'DERIVED')),
    contract_hash    TEXT NOT NULL,
    contract_version TEXT,
    status           TEXT NOT NULL
                         CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')),
    started_at       TEXT NOT NULL,
    completed_at     TEXT,
    error_message    TEXT
);

-- ---------------------------------------------------------------------------
-- 3. azm_provenance
--    Provenance record for every knowledge assertion.
--    For SOURCE_DECLARED: traces to BS → Contract → Element.
--    For AZM_DERIVED: traces to [source concept UUIDs] + derivation rule.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_provenance (
    id                    TEXT PRIMARY KEY,
    ingestion_run_id      TEXT NOT NULL REFERENCES azm_ingestion_runs(id),
    source_bs             TEXT NOT NULL,
    contract_type         TEXT NOT NULL,
    contract_hash         TEXT,
    contract_version      TEXT,
    source_element        TEXT,
    knowledge_kind        TEXT NOT NULL
                              CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    derivation_rule       TEXT,
    derivation_source_ids TEXT,       -- JSON array of concept UUIDs
    created_at            TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 4. azm_concepts
--    Semantic Concept nodes.
--    semantic_key: stable public API identifier (e.g. 'catalog.entity.sku')
--    id: AZM-generated UUID — the internal database primary key
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_concepts (
    id                       TEXT PRIMARY KEY,
    semantic_key             TEXT NOT NULL UNIQUE,
    namespace_id             TEXT NOT NULL REFERENCES azm_namespaces(id),
    concept_name             TEXT NOT NULL,
    concept_type             TEXT NOT NULL
                                 CHECK (concept_type IN (
                                     'ENTITY', 'ATTRIBUTE', 'VOCABULARY', 'CAPABILITY',
                                     'TEMPORAL', 'AGGREGATION', 'RELATIONSHIP', 'STATE'
                                 )),
    definition               TEXT,
    knowledge_kind           TEXT NOT NULL
                                 CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    version                  INTEGER NOT NULL DEFAULT 1,
    lifecycle                TEXT NOT NULL DEFAULT 'ACTIVE'
                                 CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    capability_urn           TEXT,
    capability_constraints   TEXT,    -- JSON array of semantic_key strings
    extra_metadata           TEXT,    -- JSON
    provenance_id            TEXT REFERENCES azm_provenance(id),
    created_at               TEXT NOT NULL,
    archived_at              TEXT
);

CREATE INDEX IF NOT EXISTS idx_concepts_namespace ON azm_concepts(namespace_id);
CREATE INDEX IF NOT EXISTS idx_concepts_lifecycle ON azm_concepts(lifecycle);

-- ---------------------------------------------------------------------------
-- 5. azm_aliases
--    Vocabulary / alias terms that resolve to a concept.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_aliases (
    id          TEXT PRIMARY KEY,
    concept_id  TEXT NOT NULL REFERENCES azm_concepts(id),
    alias       TEXT NOT NULL,
    lifecycle   TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_aliases_concept ON azm_aliases(concept_id);
CREATE INDEX IF NOT EXISTS idx_aliases_text    ON azm_aliases(alias);

-- ---------------------------------------------------------------------------
-- 6. azm_relationships
--    Semantic Relationship between two concepts.
--    knowledge_kind: SOURCE_DECLARED (explicitly in a contract) |
--                    AZM_DERIVED (inferred at ingestion time from multiple contracts)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_relationships (
    id                TEXT PRIMARY KEY,
    source_concept_id TEXT NOT NULL REFERENCES azm_concepts(id),
    target_concept_id TEXT NOT NULL REFERENCES azm_concepts(id),
    relationship_type TEXT NOT NULL
                          CHECK (relationship_type IN (
                              'CONTAINS', 'HAS', 'MAPS_TO', 'RELATED_TO', 'PART_OF'
                          )),
    knowledge_kind    TEXT NOT NULL
                          CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    lifecycle         TEXT NOT NULL DEFAULT 'ACTIVE'
                          CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    provenance_id     TEXT REFERENCES azm_provenance(id),
    created_at        TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 7. azm_schematic_refs
--    Schematic Reference: a governed public surface (SQL view, REST API, MCP schema).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_schematic_refs (
    id            TEXT PRIMARY KEY,
    namespace_id  TEXT NOT NULL REFERENCES azm_namespaces(id),
    ref_name      TEXT NOT NULL,
    surface_type  TEXT NOT NULL
                      CHECK (surface_type IN ('SQL_VIEW', 'REST_API', 'MCP_SCHEMA')),
    description   TEXT,
    knowledge_kind TEXT NOT NULL DEFAULT 'SOURCE_DECLARED'
                       CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    version       INTEGER NOT NULL DEFAULT 1,
    lifecycle     TEXT NOT NULL DEFAULT 'ACTIVE'
                      CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    provenance_id TEXT REFERENCES azm_provenance(id),
    created_at    TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_schematic_refs_ns_name_ver
    ON azm_schematic_refs(namespace_id, ref_name, version);

-- ---------------------------------------------------------------------------
-- 8. azm_schematic_attrs
--    Individual field / column within a Schematic Reference.
--    is_derived=1  → computed column (e.g. gross_margin)
--    is_channel_field=1 → external/channel field (e.g. shopdeck_sku_id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_schematic_attrs (
    id                TEXT PRIMARY KEY,
    schematic_ref_id  TEXT NOT NULL REFERENCES azm_schematic_refs(id),
    field_name        TEXT NOT NULL,
    field_type        TEXT,
    description       TEXT,
    is_derived        INTEGER NOT NULL DEFAULT 0
                          CHECK (is_derived IN (0, 1)),
    is_channel_field  INTEGER NOT NULL DEFAULT 0
                          CHECK (is_channel_field IN (0, 1)),
    knowledge_kind    TEXT NOT NULL DEFAULT 'SOURCE_DECLARED'
                          CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    version           INTEGER NOT NULL DEFAULT 1,
    lifecycle         TEXT NOT NULL DEFAULT 'ACTIVE'
                          CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    provenance_id     TEXT REFERENCES azm_provenance(id),
    created_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schematic_attrs_ref
    ON azm_schematic_attrs(schematic_ref_id);

-- ---------------------------------------------------------------------------
-- 9. azm_attr_mappings
--    Explicit link between a Semantic Concept and a Schematic Attribute.
--    mapping_confidence: EXPLICIT (clearly stated) | INFERRED (AZM-reasoned at ingestion)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_attr_mappings (
    id                TEXT PRIMARY KEY,
    concept_id        TEXT NOT NULL REFERENCES azm_concepts(id),
    schematic_attr_id TEXT NOT NULL REFERENCES azm_schematic_attrs(id),
    mapping_confidence TEXT NOT NULL DEFAULT 'EXPLICIT'
                           CHECK (mapping_confidence IN ('EXPLICIT', 'INFERRED')),
    knowledge_kind    TEXT NOT NULL DEFAULT 'SOURCE_DECLARED'
                          CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    version           INTEGER NOT NULL DEFAULT 1,
    lifecycle         TEXT NOT NULL DEFAULT 'ACTIVE'
                          CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    provenance_id     TEXT REFERENCES azm_provenance(id),
    created_at        TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 10. azm_external_mappings
--     Link from an AARAM_NATIVE concept to an external/channel identifier.
--     ShopDeck mappings go here — NOT into azm_concepts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS azm_external_mappings (
    id                       TEXT PRIMARY KEY,
    aaram_native_concept_id  TEXT NOT NULL REFERENCES azm_concepts(id),
    external_system          TEXT NOT NULL,
    external_key             TEXT NOT NULL,
    external_display_name    TEXT,
    knowledge_kind           TEXT NOT NULL DEFAULT 'SOURCE_DECLARED'
                                 CHECK (knowledge_kind IN ('SOURCE_DECLARED', 'AZM_DERIVED')),
    lifecycle                TEXT NOT NULL DEFAULT 'ACTIVE'
                                 CHECK (lifecycle IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED')),
    provenance_id            TEXT REFERENCES azm_provenance(id),
    created_at               TEXT NOT NULL
);
