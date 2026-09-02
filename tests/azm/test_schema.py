"""
AZM Schema Initialization Tests — Phase 1

Verifies:
A. Empty AZM database can be created
B. All 10 expected tables are present after schema execution
C. Second init call is idempotent (no error, no duplicate tables)
D. Empty DB has zero knowledge rows
E. is_initialized() returns correct True/False
"""
import sqlite3
import pytest

from src.azm.db import get_connection, execute_schema, is_initialized

# Use in-memory SQLite for all tests
DB_URL = "sqlite:///:memory:"


def _mem_url():
    """Each test that needs a fresh DB gets its own in-memory URL."""
    return "sqlite:///:memory:"


def make_conn() -> sqlite3.Connection:
    """Create a fresh in-memory connection with schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ── A. DB creation ─────────────────────────────────────────────────────────

def test_schema_can_be_applied():
    conn = make_conn()
    execute_schema(conn)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row["name"] for row in cursor.fetchall()}
    assert "azm_namespaces" in tables
    assert "azm_concepts" in tables
    conn.close()


# ── B. All 10 tables present ───────────────────────────────────────────────

EXPECTED_TABLES = {
    "azm_aliases",
    "azm_attr_mappings",
    "azm_concepts",
    "azm_external_mappings",
    "azm_ingestion_runs",
    "azm_namespaces",
    "azm_provenance",
    "azm_relationships",
    "azm_schematic_attrs",
    "azm_schematic_refs",
}


def test_all_expected_tables_present():
    conn = make_conn()
    execute_schema(conn)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {missing}"
    conn.close()


# ── C. Idempotency ─────────────────────────────────────────────────────────

def test_schema_init_is_idempotent():
    conn = make_conn()
    execute_schema(conn)
    execute_schema(conn)  # second call must not raise
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row["name"] for row in cursor.fetchall() if not row["name"].startswith("sqlite_")]
    # Table names should not be duplicated
    assert len(tables) == len(set(tables))
    conn.close()


# ── D. Empty DB has zero knowledge rows ────────────────────────────────────

def test_empty_db_has_no_knowledge_rows():
    conn = make_conn()
    execute_schema(conn)
    for table in EXPECTED_TABLES:
        cursor = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}")
        count = cursor.fetchone()["cnt"]
        assert count == 0, f"Expected 0 rows in {table}, got {count}"
    conn.close()


# ── E. is_initialized() ────────────────────────────────────────────────────

def test_is_initialized_returns_false_before_schema():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    assert not is_initialized(conn)
    conn.close()


def test_is_initialized_returns_true_after_schema():
    conn = make_conn()
    execute_schema(conn)
    assert is_initialized(conn)
    conn.close()


# ── F. Column presence spot-check ──────────────────────────────────────────

def test_azm_concepts_has_required_columns():
    conn = make_conn()
    execute_schema(conn)
    cursor = conn.execute("PRAGMA table_info(azm_concepts)")
    columns = {row["name"] for row in cursor.fetchall()}
    required = {
        "id", "semantic_key", "namespace_id", "concept_name", "concept_type",
        "definition", "knowledge_kind", "version", "lifecycle",
        "capability_urn", "capability_constraints", "provenance_id", "created_at",
    }
    missing = required - columns
    assert not missing, f"azm_concepts missing columns: {missing}"
    conn.close()


def test_azm_schematic_attrs_has_is_derived_and_is_channel():
    conn = make_conn()
    execute_schema(conn)
    cursor = conn.execute("PRAGMA table_info(azm_schematic_attrs)")
    columns = {row["name"] for row in cursor.fetchall()}
    assert "is_derived" in columns
    assert "is_channel_field" in columns
    conn.close()


def test_azm_provenance_has_knowledge_kind_and_derivation_fields():
    conn = make_conn()
    execute_schema(conn)
    cursor = conn.execute("PRAGMA table_info(azm_provenance)")
    columns = {row["name"] for row in cursor.fetchall()}
    assert "knowledge_kind" in columns
    assert "derivation_rule" in columns
    assert "derivation_source_ids" in columns
    conn.close()
