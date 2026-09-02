"""
AZM Persistent Provider Tests — Phase 3

Verifies that the PersistentAzmProvider correctly implements the AzmProvider
Protocol and reconstructs objects perfectly from DB rows, maintaining
full backward compatibility with the existing Python dict-based behavior.
"""
import sqlite3
import pytest

from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.catalog_ingester import ingest_catalog
from src.azm.persistent_provider import PersistentAzmProvider
from src.azm.provider import AzmProviderFactory, GlobalAzmProvider


@pytest.fixture
def seeded_db_url():
    """Returns a DB URL that is already initialized and seeded with Catalog."""
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite:///{tmp.name}"
    
    # Init and ingest
    conn = get_connection(db_url)
    execute_schema(conn)
    conn.close()
    
    res = ingest_catalog(db_url=db_url)
    assert res["status"] == "COMPLETED"
    
    yield db_url
    os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Test PersistentAzmProvider
# ---------------------------------------------------------------------------

class TestPersistentAzmProvider:
    def test_init_raises_if_db_uninitialized(self):
        """Should raise if pointing to a file without the AZM schema."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_url = f"sqlite:///{tmp.name}"
        
        with pytest.raises(RuntimeError, match="not initialized"):
            PersistentAzmProvider(db_url=db_url)
            
        os.unlink(tmp.name)

    def test_get_concept_by_id(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        concept = provider.get_concept_by_id("catalog.entity.sku")
        
        assert concept.concept_id == "catalog.entity.sku"
        assert concept.concept_name == "SKU"
        assert concept.concept_type == "ENTITY"
        assert "sku" in concept.aliases
        assert "sellable unit" in concept.aliases

    def test_get_concept_by_id_raises_value_error_if_not_found(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        with pytest.raises(ValueError, match="not found in Azm"):
            provider.get_concept_by_id("does.not.exist")

    def test_search_concepts_by_namespace_exact_match(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        results = provider.search_concepts_by_namespace("catalog", "sku")
        assert len(results) >= 1
        assert any(c.concept_id == "catalog.entity.sku" for c in results)

    def test_search_concepts_by_namespace_alias_match(self, seeded_db_url):
        """Search should hit on aliases too (e.g. 'sellable unit' -> sku)"""
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        results = provider.search_concepts_by_namespace("catalog", "sellable unit")
        assert len(results) >= 1
        assert any(c.concept_id == "catalog.entity.sku" for c in results)

    def test_search_concepts_raises_value_error_on_bad_namespace(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        with pytest.raises(ValueError, match="Unknown namespace"):
            provider.search_concepts_by_namespace("bad_namespace", "query")

    def test_get_namespace_schema(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        schema = provider.get_namespace_schema("catalog")
        
        assert "vw_catalog_skus" in schema
        assert "vw_catalog_products" in schema
        
        sku_cols = schema["vw_catalog_skus"]["columns"]
        assert "selling_price" in sku_cols
        # Check it formats as "TYPE - desc"
        assert sku_cols["selling_price"].startswith("NUMERIC -")
        
    def test_get_namespace_schema_raises_value_error_on_bad_namespace(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        with pytest.raises(ValueError, match="Unknown namespace"):
            provider.get_namespace_schema("bad_namespace")
            
    def test_get_schematic_attr(self, seeded_db_url):
        provider = PersistentAzmProvider(db_url=seeded_db_url)
        
        attr = provider.get_schematic_attr("catalog", "vw_catalog_skus", "gross_margin")
        assert attr is not None
        assert attr["is_derived"] is True
        assert attr["mapped_concept"] == "catalog.entity.sku"
        
        # Test ShopDeck token
        attr2 = provider.get_schematic_attr("catalog", "vw_catalog_master", "shopdeck_sku_id")
        assert attr2 is not None
        assert attr2["is_channel_field"] is True
        # NOTE: it is an external mapping, so mapped_concept will be None since it's not in azm_attr_mappings
        assert attr2["mapped_concept"] is None
        
        # Test non-existent
        assert provider.get_schematic_attr("catalog", "vw_catalog_skus", "bad_col") is None


# ---------------------------------------------------------------------------
# Test AzmProviderFactory
# ---------------------------------------------------------------------------

class TestAzmProviderFactory:
    def test_factory_returns_persistent_if_db_valid(self, seeded_db_url):
        provider = AzmProviderFactory.create(db_url=seeded_db_url)
        assert isinstance(provider, PersistentAzmProvider)

    def test_factory_falls_back_to_global_if_db_uninitialized(self, caplog):
        """If the DB file exists but has no schema, fallback to Global."""
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_url = f"sqlite:///{tmp.name}"
        
        provider = AzmProviderFactory.create(db_url=db_url)
        assert isinstance(provider, GlobalAzmProvider)
        assert "AZM persistent provider unavailable" in caplog.text
        
        os.unlink(tmp.name)

    def test_factory_falls_back_to_global_if_db_missing(self, caplog):
        """If the DB path is totally invalid, fallback to Global."""
        provider = AzmProviderFactory.create(db_url="sqlite:////tmp/does/not/exist/ever.db")
        assert isinstance(provider, GlobalAzmProvider)
        assert "AZM persistent provider unavailable" in caplog.text
