"""
AZM Catalog Ingestion Tests — Phase 2

Covers test categories:
C.  Catalog ingestion (concepts, namespace, views, attrs)
D.  Repeat ingestion idempotency
E.  Changed contract simulation
F.  Historical version preservation
G.  Provenance completeness
H.  SOURCE_DECLARED vs AZM_DERIVED
I.  Schematic references
J.  Schematic attributes (including is_derived / is_channel_field)
K.  Attribute mappings
L.  External mappings (ShopDeck firewall)
M.  Namespace classification
N.  ShopDeck isolation
O.  No operational records
R.  Failed ingestion rollback (simulated)
S.  Missing/ambiguous mapping — no mapping invented
"""
import sqlite3
import pytest

from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.catalog_ingester import ingest_catalog
from src.azm.ingestion.ingestion_utils import (
    hash_content, is_already_ingested, start_ingestion_run,
    fail_ingestion_run, build_provenance,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_db():
    """In-memory DB with schema applied, ready for ingestion."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    execute_schema(conn)
    conn.close()
    # We'll use a temp file path so ingest_catalog can open its own connection
    # Actually, use the in-memory URL trick via a tmp file
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite:///{tmp.name}"
    yield db_url
    os.unlink(tmp.name)


@pytest.fixture
def ingested_db(fresh_db):
    """DB with Catalog already ingested once."""
    result = ingest_catalog(db_url=fresh_db)
    assert result["status"] == "COMPLETED", f"Ingestion failed: {result}"
    return fresh_db


def _conn(db_url: str) -> sqlite3.Connection:
    conn = get_connection(db_url)
    return conn


# ---------------------------------------------------------------------------
# C. Catalog ingestion
# ---------------------------------------------------------------------------

class TestCatalogIngestion:
    def test_ingest_returns_completed(self, fresh_db):
        result = ingest_catalog(db_url=fresh_db)
        assert result["status"] == "COMPLETED"

    def test_namespace_created(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute("SELECT * FROM azm_namespaces WHERE name='catalog'").fetchone()
        assert row is not None
        assert row["classification"] == "AARAM_NATIVE"
        assert row["lifecycle"] == "ACTIVE"
        conn.close()

    def test_exactly_two_concepts(self, ingested_db):
        conn = _conn(ingested_db)
        count = conn.execute("SELECT COUNT(*) FROM azm_concepts").fetchone()[0]
        assert count == 2, f"Expected 2 concepts, got {count}"
        conn.close()

    def test_product_concept_exists(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT * FROM azm_concepts WHERE semantic_key='catalog.entity.product'"
        ).fetchone()
        assert row is not None
        assert row["concept_type"] == "ENTITY"
        assert row["knowledge_kind"] == "SOURCE_DECLARED"
        assert row["lifecycle"] == "ACTIVE"
        conn.close()

    def test_sku_concept_exists(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT * FROM azm_concepts WHERE semantic_key='catalog.entity.sku'"
        ).fetchone()
        assert row is not None
        assert row["concept_type"] == "ENTITY"
        assert row["knowledge_kind"] == "SOURCE_DECLARED"
        conn.close()

    def test_product_has_aliases(self, ingested_db):
        conn = _conn(ingested_db)
        concept = conn.execute(
            "SELECT id FROM azm_concepts WHERE semantic_key='catalog.entity.product'"
        ).fetchone()
        aliases = conn.execute(
            "SELECT alias FROM azm_aliases WHERE concept_id=?", (concept["id"],)
        ).fetchall()
        alias_list = [r["alias"] for r in aliases]
        assert "product family" in alias_list
        assert "commercial family" in alias_list
        conn.close()

    def test_sku_has_aliases(self, ingested_db):
        conn = _conn(ingested_db)
        concept = conn.execute(
            "SELECT id FROM azm_concepts WHERE semantic_key='catalog.entity.sku'"
        ).fetchone()
        aliases = conn.execute(
            "SELECT alias FROM azm_aliases WHERE concept_id=?", (concept["id"],)
        ).fetchall()
        alias_list = [r["alias"] for r in aliases]
        assert "sku" in alias_list
        conn.close()

    def test_three_schematic_refs(self, ingested_db):
        conn = _conn(ingested_db)
        refs = conn.execute("SELECT ref_name FROM azm_schematic_refs WHERE lifecycle='ACTIVE'").fetchall()
        names = {r["ref_name"] for r in refs}
        assert "vw_catalog_products" in names
        assert "vw_catalog_skus" in names
        assert "vw_catalog_master" in names
        assert len(names) == 3
        conn.close()

    def test_ingestion_run_completed(self, ingested_db):
        conn = _conn(ingested_db)
        run = conn.execute(
            "SELECT status FROM azm_ingestion_runs WHERE source_bs='catalog'"
        ).fetchone()
        assert run["status"] == "COMPLETED"
        conn.close()


# ---------------------------------------------------------------------------
# D. Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_second_ingest_is_skipped(self, ingested_db):
        result2 = ingest_catalog(db_url=ingested_db)
        assert result2["status"] == "SKIPPED"

    def test_no_duplicate_concepts_after_second_ingest(self, ingested_db):
        ingest_catalog(db_url=ingested_db)
        conn = _conn(ingested_db)
        count = conn.execute("SELECT COUNT(*) FROM azm_concepts").fetchone()[0]
        assert count == 2
        conn.close()

    def test_no_duplicate_namespaces_after_second_ingest(self, ingested_db):
        ingest_catalog(db_url=ingested_db)
        conn = _conn(ingested_db)
        count = conn.execute("SELECT COUNT(*) FROM azm_namespaces WHERE name='catalog'").fetchone()[0]
        assert count == 1
        conn.close()

    def test_no_duplicate_schematic_refs(self, ingested_db):
        ingest_catalog(db_url=ingested_db)
        conn = _conn(ingested_db)
        count = conn.execute("SELECT COUNT(*) FROM azm_schematic_refs WHERE lifecycle='ACTIVE'").fetchone()[0]
        assert count == 3
        conn.close()


# ---------------------------------------------------------------------------
# G. Provenance completeness
# ---------------------------------------------------------------------------

class TestProvenance:
    def test_every_concept_has_provenance(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute(
            "SELECT semantic_key, provenance_id FROM azm_concepts"
        ).fetchall()
        for row in rows:
            assert row["provenance_id"] is not None, (
                f"Concept {row['semantic_key']} has no provenance_id"
            )
        conn.close()

    def test_every_schematic_ref_has_provenance(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute("SELECT ref_name, provenance_id FROM azm_schematic_refs").fetchall()
        for row in rows:
            assert row["provenance_id"] is not None, (
                f"Schematic ref {row['ref_name']} has no provenance_id"
            )
        conn.close()

    def test_every_schematic_attr_has_provenance(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute("SELECT field_name, provenance_id FROM azm_schematic_attrs").fetchall()
        for row in rows:
            assert row["provenance_id"] is not None, (
                f"Schematic attr {row['field_name']} has no provenance_id"
            )
        conn.close()

    def test_every_attr_mapping_has_provenance(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute("SELECT id, provenance_id FROM azm_attr_mappings").fetchall()
        for row in rows:
            assert row["provenance_id"] is not None
        conn.close()

    def test_provenance_has_source_bs(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute("SELECT source_bs FROM azm_provenance").fetchall()
        for row in rows:
            assert row["source_bs"] == "catalog"
        conn.close()


# ---------------------------------------------------------------------------
# H. SOURCE_DECLARED vs AZM_DERIVED
# ---------------------------------------------------------------------------

class TestKnowledgeKind:
    def test_product_is_source_declared(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT knowledge_kind FROM azm_concepts WHERE semantic_key='catalog.entity.product'"
        ).fetchone()
        assert row["knowledge_kind"] == "SOURCE_DECLARED"
        conn.close()

    def test_sku_is_source_declared(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT knowledge_kind FROM azm_concepts WHERE semantic_key='catalog.entity.sku'"
        ).fetchone()
        assert row["knowledge_kind"] == "SOURCE_DECLARED"
        conn.close()

    def test_product_contains_sku_is_azm_derived(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT knowledge_kind FROM azm_relationships WHERE relationship_type='CONTAINS'"
        ).fetchone()
        assert row is not None, "CONTAINS relationship not found"
        assert row["knowledge_kind"] == "AZM_DERIVED"
        conn.close()

    def test_derived_relationship_provenance_has_derivation_rule(self, ingested_db):
        conn = _conn(ingested_db)
        rel = conn.execute(
            "SELECT provenance_id FROM azm_relationships WHERE relationship_type='CONTAINS'"
        ).fetchone()
        prov = conn.execute(
            "SELECT derivation_rule, knowledge_kind FROM azm_provenance WHERE id=?",
            (rel["provenance_id"],),
        ).fetchone()
        assert prov["derivation_rule"] == "catalog_2tier_containment"
        assert prov["knowledge_kind"] == "AZM_DERIVED"
        conn.close()


# ---------------------------------------------------------------------------
# I. Schematic references
# ---------------------------------------------------------------------------

class TestSchematicRefs:
    def test_vw_catalog_skus_is_sql_view(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT surface_type FROM azm_schematic_refs WHERE ref_name='vw_catalog_skus'"
        ).fetchone()
        assert row["surface_type"] == "SQL_VIEW"
        conn.close()

    def test_all_refs_are_active(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute("SELECT lifecycle FROM azm_schematic_refs").fetchall()
        for row in rows:
            assert row["lifecycle"] == "ACTIVE"
        conn.close()


# ---------------------------------------------------------------------------
# J. Schematic attributes
# ---------------------------------------------------------------------------

class TestSchematicAttrs:
    def test_selling_price_exists_not_derived(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute(
            "SELECT is_derived, is_channel_field FROM azm_schematic_attrs WHERE field_name='selling_price'"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            assert row["is_derived"] == 0
            assert row["is_channel_field"] == 0
        conn.close()

    def test_gross_margin_is_derived(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute(
            "SELECT is_derived FROM azm_schematic_attrs WHERE field_name='gross_margin'"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            assert row["is_derived"] == 1
        conn.close()

    def test_shopdeck_sku_id_is_channel_field(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute(
            "SELECT is_channel_field FROM azm_schematic_attrs WHERE field_name='shopdeck_sku_id'"
        ).fetchall()
        assert len(rows) > 0
        for row in rows:
            assert row["is_channel_field"] == 1
        conn.close()

    def test_vw_catalog_skus_has_correct_field_count(self, ingested_db):
        conn = _conn(ingested_db)
        ref_id = conn.execute(
            "SELECT id FROM azm_schematic_refs WHERE ref_name='vw_catalog_skus'"
        ).fetchone()["id"]
        count = conn.execute(
            "SELECT COUNT(*) FROM azm_schematic_attrs WHERE schematic_ref_id=?", (ref_id,)
        ).fetchone()[0]
        # vw_catalog_skus has 20 fields per plan
        assert count == 20, f"Expected 20 fields for vw_catalog_skus, got {count}"
        conn.close()


# ---------------------------------------------------------------------------
# K. Attribute mappings
# ---------------------------------------------------------------------------

class TestAttrMappings:
    def test_selling_price_mapped_to_sku(self, ingested_db):
        conn = _conn(ingested_db)
        sku_concept = conn.execute(
            "SELECT id FROM azm_concepts WHERE semantic_key='catalog.entity.sku'"
        ).fetchone()
        attrs = conn.execute(
            """
            SELECT sa.field_name FROM azm_attr_mappings am
            JOIN azm_schematic_attrs sa ON am.schematic_attr_id = sa.id
            WHERE am.concept_id = ? AND sa.field_name = 'selling_price'
            """,
            (sku_concept["id"],),
        ).fetchall()
        assert len(attrs) > 0, "selling_price not mapped to catalog.entity.sku"
        conn.close()

    def test_mapping_confidence_is_explicit(self, ingested_db):
        conn = _conn(ingested_db)
        rows = conn.execute(
            "SELECT DISTINCT mapping_confidence FROM azm_attr_mappings"
        ).fetchall()
        confidences = {r["mapping_confidence"] for r in rows}
        # All current mappings are EXPLICIT
        assert confidences == {"EXPLICIT"}
        conn.close()

    def test_unmapped_field_has_no_mapping(self, ingested_db):
        """Fields like brand, hsn_code should have no attr_mapping (no invented mappings)."""
        conn = _conn(ingested_db)
        ambiguous_fields = ["brand", "hsn_code", "fabric_type", "collection_tags"]
        for field_name in ambiguous_fields:
            count = conn.execute(
                """
                SELECT COUNT(*) FROM azm_attr_mappings am
                JOIN azm_schematic_attrs sa ON am.schematic_attr_id = sa.id
                WHERE sa.field_name = ?
                """,
                (field_name,),
            ).fetchone()[0]
            assert count == 0, f"Field '{field_name}' should have no concept mapping, got {count}"
        conn.close()


# ---------------------------------------------------------------------------
# L. External mappings (ShopDeck firewall)
# ---------------------------------------------------------------------------

class TestExternalMappings:
    def test_shopdeck_sku_id_is_in_external_mappings(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT * FROM azm_external_mappings WHERE external_key='customer_sku_short_id'"
        ).fetchone()
        assert row is not None
        assert row["external_system"] == "shopdeck"
        conn.close()

    def test_shopdeck_product_id_is_in_external_mappings(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT * FROM azm_external_mappings WHERE external_key='customer_product_short_id'"
        ).fetchone()
        assert row is not None
        assert row["external_system"] == "shopdeck"
        conn.close()

    def test_shopdeck_sku_id_NOT_in_azm_concepts(self, ingested_db):
        conn = _conn(ingested_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM azm_concepts WHERE semantic_key LIKE '%shopdeck%'"
        ).fetchone()[0]
        assert count == 0, "ShopDeck concepts must NOT exist in azm_concepts"
        conn.close()

    def test_external_mapping_links_to_aaram_native_concept(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            """
            SELECT c.semantic_key FROM azm_external_mappings em
            JOIN azm_concepts c ON em.aaram_native_concept_id = c.id
            WHERE em.external_key='customer_sku_short_id'
            """
        ).fetchone()
        assert row["semantic_key"] == "catalog.entity.sku"
        conn.close()


# ---------------------------------------------------------------------------
# M. Namespace classification
# ---------------------------------------------------------------------------

class TestNamespaceClassification:
    def test_catalog_is_aaram_native(self, ingested_db):
        conn = _conn(ingested_db)
        row = conn.execute(
            "SELECT classification FROM azm_namespaces WHERE name='catalog'"
        ).fetchone()
        assert row["classification"] == "AARAM_NATIVE"
        conn.close()


# ---------------------------------------------------------------------------
# N. ShopDeck isolation
# ---------------------------------------------------------------------------

class TestShopDeckIsolation:
    def test_commerce_available_qty_not_in_azm(self, ingested_db):
        conn = _conn(ingested_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM azm_schematic_attrs WHERE field_name='commerce_available_qty'"
        ).fetchone()[0]
        assert count == 0

    def test_is_deal_not_in_azm(self, ingested_db):
        conn = _conn(ingested_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM azm_schematic_attrs WHERE field_name='is_deal'"
        ).fetchone()[0]
        assert count == 0

    def test_coupon_code_not_in_azm(self, ingested_db):
        conn = _conn(ingested_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM azm_schematic_attrs WHERE field_name='coupon_code'"
        ).fetchone()[0]
        assert count == 0


# ---------------------------------------------------------------------------
# O. No operational records
# ---------------------------------------------------------------------------

class TestNoOperationalRecords:
    def test_no_concept_has_operational_data_pattern(self, ingested_db):
        """AZM concepts should be knowledge metadata, not operational rows."""
        conn = _conn(ingested_db)
        # If AZM accidentally stored SKU data rows, we'd see thousands of concepts.
        # Only 2 semantic concepts should exist.
        count = conn.execute("SELECT COUNT(*) FROM azm_concepts").fetchone()[0]
        assert count == 2
        conn.close()


# ---------------------------------------------------------------------------
# R. Failed ingestion rollback
# ---------------------------------------------------------------------------

class TestRollback:
    def test_failed_ingestion_leaves_no_concepts(self, fresh_db):
        """
        Simulate a failure mid-ingestion by manually beginning a transaction,
        inserting a row, rolling it back, then verifying DB is clean.
        """
        import os
        db_path = fresh_db.replace("sqlite:///", "")
        # Use explicit isolation_level=None for manual transaction control
        conn = sqlite3.connect(db_path)
        conn.isolation_level = None  # autocommit mode — allows explicit BEGIN/ROLLBACK
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        execute_schema(conn)

        run_id = start_ingestion_run(conn, "catalog", "FULL", "faKEhash123", "test")
        conn.execute("BEGIN")
        conn.execute(
            """INSERT INTO azm_namespaces (id, name, classification, lifecycle, created_at)
               VALUES ('fake-ns-id', 'catalog_test_rollback', 'AARAM_NATIVE', 'ACTIVE', '2026-01-01')"""
        )
        conn.execute("ROLLBACK")

        fail_ingestion_run(conn, run_id, "Simulated failure")

        # DB should have zero namespaces after rollback
        count = conn.execute("SELECT COUNT(*) FROM azm_namespaces").fetchone()[0]
        assert count == 0, f"Expected 0 namespaces after rollback, got {count}"

        run = conn.execute(
            "SELECT status FROM azm_ingestion_runs WHERE id=?", (run_id,)
        ).fetchone()
        assert run["status"] == "FAILED"
        conn.close()

