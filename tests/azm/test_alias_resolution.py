import pytest
from src.azm.persistent_provider import PersistentAzmProvider
from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.universal_ingester import UniversalAzmIngester, AzmIngestionConfig, AzmConceptDef

@pytest.fixture(scope="module")
def setup_test_db():
    import tempfile
    import os
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    conn = get_connection(db_url)
    execute_schema(conn)
    
    # Ingest some test data
    config = AzmIngestionConfig(
        source_bs="test_sys",
        namespace_name="test_ns",
        namespace_classification="AARAM_NATIVE",
        namespace_description="Test Namespace",
        contract_version="1.0",
        semantic_contract_content="",
        schematic_contract_content="",
        semantic_source_element="test.md",
        schematic_source_element="test.md",
        concepts=[
            AzmConceptDef(
                semantic_key="test.concept.exact",
                concept_name="Exact Match Concept",
                concept_type="ENTITY",
                definition="A concept for exact match testing",
                source_element="test",
                aliases=["exact_alias", "Exact_Alias_Mixed_Case"]
            ),
            AzmConceptDef(
                semantic_key="test.concept.fuzzy1",
                concept_name="Fuzzy Concept 1",
                concept_type="ENTITY",
                definition="A concept for fuzzy match testing",
                source_element="test",
                aliases=["some_long_alias_string"]
            ),
            AzmConceptDef(
                semantic_key="test.concept.ambiguous1",
                concept_name="Ambiguous Concept 1",
                concept_type="ENTITY",
                definition="First ambiguous concept",
                source_element="test",
                aliases=["shared_alias"]
            ),
            AzmConceptDef(
                semantic_key="test.concept.ambiguous2",
                concept_name="Ambiguous Concept 2",
                concept_type="ENTITY",
                definition="Second ambiguous concept",
                source_element="test",
                aliases=["shared_alias"]
            ),
        ],
        relationships=[],
        views=[],
        external_mappings=[]
    )
    ingester = UniversalAzmIngester(db_url)
    ingester.ingest(config)
    
    # Deprecated concept ingestion
    run_id = "dep_run_1"
    conn.execute("INSERT INTO azm_ingestion_runs (id, source_bs, contract_type, status, contract_hash, started_at) VALUES (?, ?, ?, ?, ?, ?)", (run_id, "test_sys", "FULL", "COMPLETED", "hash", "2023-01-01T00:00:00Z"))
    prov_id = "prov_1"
    conn.execute("INSERT INTO azm_provenance (id, ingestion_run_id, source_bs, contract_type, knowledge_kind, created_at) VALUES (?, ?, ?, ?, ?, ?)", (prov_id, run_id, "test_sys", "SEMANTIC", "SOURCE_DECLARED", "2023-01-01T00:00:00Z"))
    ns_row = conn.execute("SELECT id FROM azm_namespaces WHERE name='test_ns'").fetchone()
    if ns_row:
        ns_id = ns_row[0]
    else:
        ns_id = "test_ns_id"
        conn.execute("INSERT INTO azm_namespaces (id, name, classification, created_at) VALUES (?, ?, ?, ?)", (ns_id, "test_ns", "AARAM_NATIVE", "2023-01-01T00:00:00Z"))
    
    c_id = "dep_concept_1"
    conn.execute("INSERT INTO azm_concepts (id, namespace_id, semantic_key, concept_name, concept_type, knowledge_kind, provenance_id, lifecycle, definition, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'ARCHIVED', ?, ?)", 
                 (c_id, ns_id, "test.concept.deprecated", "Dep Concept", "ENTITY", "SOURCE_DECLARED", prov_id, "Deprecated concept", "2023-01-01T00:00:00Z"))
    conn.execute("INSERT INTO azm_aliases (id, concept_id, alias, lifecycle, created_at) VALUES (?, ?, ?, 'ARCHIVED', ?)", ("a1", c_id, "deprecated_alias", "2023-01-01T00:00:00Z"))
    conn.commit()
    conn.close()
    
    return db_url

def test_exact_unique_alias_one_concept(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    results = provider.resolve_concepts_by_alias("exact_alias")
    assert len(results) == 1
    assert results[0].concept_id == "test.concept.exact"

def test_unknown_alias_empty_result(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    results = provider.resolve_concepts_by_alias("unknown_alias_123")
    assert len(results) == 0

def test_multiple_concepts_sharing_alias_all_returned(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    results = provider.resolve_concepts_by_alias("shared_alias")
    assert len(results) == 2
    concept_ids = [r.concept_id for r in results]
    assert "test.concept.ambiguous1" in concept_ids
    assert "test.concept.ambiguous2" in concept_ids

def test_fuzzy_substring_match_does_not_count(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    results = provider.resolve_concepts_by_alias("some_long_alias") # Missing _string
    assert len(results) == 0

def test_case_normalization_deterministic(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    # Test case insensitivity 
    results = provider.resolve_concepts_by_alias("ExAcT_AlIaS_MiXeD_CaSe")
    assert len(results) == 1
    assert results[0].concept_id == "test.concept.exact"

def test_deprecated_inactive_concept_behavior(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    results = provider.resolve_concepts_by_alias("deprecated_alias")
    assert len(results) == 0

def test_idempotent_repeated_resolution(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    results1 = provider.resolve_concepts_by_alias("exact_alias")
    results2 = provider.resolve_concepts_by_alias("exact_alias")
    assert results1[0].concept_id == results2[0].concept_id

def test_existing_namespace_search_behavior_unchanged(setup_test_db):
    provider = PersistentAzmProvider(setup_test_db)
    # Fuzzy match should still work via namespace search
    results = provider.search_concepts_by_namespace("test_ns", "long_alias_string")
    assert len(results) == 1
    assert results[0].concept_id == "test.concept.fuzzy1"
