import pytest
from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.universal_ingester import UniversalAzmIngester, AzmIngestionConfig, AzmConceptDef, AzmSchematicViewDef, AzmSchematicFieldDef
import uuid

@pytest.fixture
def clean_db():
    conn = get_connection("sqlite:///:memory:")
    execute_schema(conn)
    yield conn
    conn.close()

def build_config(version: str, desc: str) -> AzmIngestionConfig:
    return AzmIngestionConfig(
        source_bs="test_bs",
        namespace_name="test_ns",
        namespace_classification="AARAM_NATIVE",
        namespace_description="Test Namespace",
        contract_version=version,
        semantic_contract_content=f"sem v{version} {desc}",
        schematic_contract_content=f"sch v{version} {desc}",
        semantic_source_element="sem.md",
        schematic_source_element="sch.md",
        concepts=[
            AzmConceptDef(
                semantic_key="test.concept.foo",
                concept_name="Foo Concept",
                concept_type="ENTITY",
                definition=desc,
                source_element="sem.md",
                aliases=["foo"]
            )
        ],
        relationships=[],
        views=[
            AzmSchematicViewDef(
                view_name="vw_test_foo",
                description="Foo view",
                surface_type="SQL_VIEW",
                fields=[
                    AzmSchematicFieldDef(
                        field_name="foo_id",
                        field_type="TEXT",
                        description=desc,
                        mapped_concept_key="test.concept.foo"
                    )
                ]
            )
        ],
        external_mappings=[]
    )

def test_ingestion_idempotency(clean_db):
    ingester = UniversalAzmIngester(db_url="sqlite:///:memory:")
    # We share the same db connection for testing by hacking it
    ingester.db_url = "sqlite:///:memory:"
    # Actually wait, sqlite:///:memory: is thread-local in tests.
    # Let's use a file-based temporary db.
    import tempfile
    import os
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    
    db_url = f"sqlite:///{db_path}"
    ingester = UniversalAzmIngester(db_url=db_url)
    
    try:
        # TEST A: v1 -> ingest -> ingest v1 again
        config_v1 = build_config("1.0", "Original definition")
        res1 = ingester.ingest(config_v1)
        assert res1["status"] == "COMPLETED"
        
        # Second time should skip because hash is identical
        res2 = ingester.ingest(config_v1)
        assert res2["status"] == "SKIPPED"
        
        conn = get_connection(db_url)
        c_count = conn.execute("SELECT count(*) FROM azm_concepts").fetchone()[0]
        assert c_count == 1
        
        v_count = conn.execute("SELECT count(*) FROM azm_schematic_refs").fetchone()[0]
        assert v_count == 1
        
        # TEST B: v1 -> ingest -> v2 -> ingest
        config_v2 = build_config("2.0", "Updated definition")
        res3 = ingester.ingest(config_v2)
        assert res3["status"] == "COMPLETED"
        
        c_count_v2 = conn.execute("SELECT count(*) FROM azm_concepts").fetchone()[0]
        assert c_count_v2 == 1 # Identity is stable!
        
        # Verify it was updated
        definition = conn.execute("SELECT definition FROM azm_concepts").fetchone()[0]
        assert definition == "Updated definition"
        
        # TEST C: v1 -> v1 -> v2 -> v2
        res4 = ingester.ingest(config_v2)
        assert res4["status"] == "SKIPPED"
        
        conn.close()
    finally:
        os.unlink(db_path)
