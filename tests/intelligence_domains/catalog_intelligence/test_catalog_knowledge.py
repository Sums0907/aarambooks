import pytest
import os
import sqlite3
import json

from src.azm.persistent_provider import PersistentAzmProvider
from src.azm.ingestion.contract_parser import ingest_contracts
from src.azm.db import get_connection, execute_schema

from src.intelligence_domains.catalog_intelligence.knowledge import CatalogSemanticKnowledge
from src.intelligence_domains.catalog_intelligence.models import (
    CandidateProduct,
    CandidateSKU,
    ResolutionDecision,
    DecisionStatus
)


@pytest.fixture(scope="module")
def persistent_azm_provider():
    """
    Sets up a temporary SQLite DB, applies AZM schema, ingests Catalog contracts, 
    and returns a PersistentAzmProvider pointing to it.
    This guarantees we test against real Persistent AZM, not legacy dicts.
    """
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite:///{tmp.name}"
    
    conn = get_connection(db_url)
    execute_schema(conn)
    conn.close()
    
    # Ingest catalog to populate AZM knowledge DB
    res = ingest_contracts(
        "business_systems/catalog/public-contracts/catalog-semantic-public-contract.md",
        "business_systems/catalog/public-contracts/catalog-schematic-public-contract.md",
        db_url=db_url
    )
    assert res["status"] == "COMPLETED"
    
    provider = PersistentAzmProvider(db_url=db_url)
    yield provider
    
    os.unlink(tmp.name)


@pytest.fixture
def catalog_knowledge(persistent_azm_provider):
    return CatalogSemanticKnowledge(persistent_azm_provider)


# ---------------------------------------------------------------------------
# AZM Boundary Tests
# ---------------------------------------------------------------------------

def test_get_product_knowledge_through_azm(catalog_knowledge):
    product = catalog_knowledge.get_product_concept()
    assert product.concept_id == "catalog.entity.product"
    assert product.concept_type == "ENTITY"
    assert "product" in product.aliases


def test_get_sku_knowledge_through_azm(catalog_knowledge):
    sku = catalog_knowledge.get_sku_concept()
    assert sku.concept_id == "catalog.entity.sku"
    assert sku.concept_type == "ENTITY"
    assert "sellable unit" in sku.aliases


def test_get_catalog_views_through_azm(catalog_knowledge):
    views = catalog_knowledge.get_catalog_views()
    assert "vw_catalog_master" in views
    assert "vw_catalog_products" in views
    assert "vw_catalog_skus" in views
    
    master_cols = views["vw_catalog_master"]["columns"]
    assert "shopdeck_sku_id" in master_cols
    assert "sku_id" in master_cols


def test_get_schematic_attribute_through_azm(catalog_knowledge):
    # Test derived field
    attr = catalog_knowledge.get_schematic_attribute("vw_catalog_master", "gross_margin")
    assert attr is not None
    assert attr["is_derived"] is True
    assert attr["mapped_concept"] == "catalog.entity.sku"
    
    # Test channel field
    attr_channel = catalog_knowledge.get_schematic_attribute("vw_catalog_master", "shopdeck_sku_id")
    assert attr_channel is not None
    assert attr_channel["is_channel_field"] is True
    assert attr_channel["mapped_concept"] is None  # Handled as external mapping


# ---------------------------------------------------------------------------
# Model Integrity Tests
# ---------------------------------------------------------------------------

def test_candidate_models_are_non_authoritative():
    """
    Ensure the models can be instantiated as working proposals without strict
    database constraints (since Catalog BS is the ultimate validator).
    """
    sku = CandidateSKU(
        proposed_sku_id="CANDIDATE-123",
        attributes={"colour": "Red"}
    )
    
    product = CandidateProduct(
        proposed_product_code="PROD-ABC",
        attributes={"product_name": "Red T-Shirt"},
        candidate_skus=[sku]
    )
    
    proposal = ResolutionDecision(
        status=DecisionStatus.PROPOSE_NEW,
        candidate_product=product,
        reasoning="Extracted colour from text"
    )
    
    assert proposal.candidate_product.candidate_skus[0].attributes["colour"] == "Red"
    assert proposal.status == DecisionStatus.PROPOSE_NEW


def test_no_catalog_bs_imports():
    """
    Statically verify that the Catalog ID boundary does not import from the Catalog BS.
    """
    import inspect
    import src.intelligence_domains.catalog_intelligence.knowledge as knowledge_module
    
    source = inspect.getsource(knowledge_module)
    assert "business_systems.catalog" not in source, "Catalog ID must not bypass AZM to read BS directly"

# ---------------------------------------------------------------------------
# Phase K5: Catalog SABAQ Integration Boundary Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_catalog_sabaq_provider_integration():
    from unittest.mock import MagicMock
    from src.infrastructure.adapters.postgres_sabaq import PostgresSabaqProvider, SabaqEvidenceRecord
    
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    mock_record = SabaqEvidenceRecord(
        id="test-123",
        domain_namespace="catalog",
        provenance="BUSINESS_SYSTEM_HISTORY",
        evidence_version=1,
        search_content="blue floral queen bedsheet",
        structured_payload={"Product Code": "BDBLUFLO", "Sku Id": "BDBLUFLO-Q"},
        metadata_={"product_type": "BED", "colour": "blue"}
    )
    
    mock_result.scalars.return_value.all.return_value = [mock_record]
    
    async def mock_execute(*args, **kwargs):
        return mock_result
        
    mock_session.execute = mock_execute
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    mock_factory = MagicMock(return_value=mock_session_context)
    
    provider = PostgresSabaqProvider(mock_factory)
    
    # Prove Catalog can query historical evidence cleanly
    results = await provider.retrieve_evidence("catalog", "blue floral queen bedsheet")
    
    assert len(results) == 1
    evidence = results[0]
    assert evidence.domain_namespace == "catalog"
    assert evidence.provenance.value == "BUSINESS_SYSTEM_HISTORY"
    assert evidence.structured_payload["Sku Id"] == "BDBLUFLO-Q"
