import pytest
import os
import tempfile
from typing import Dict, Any

from src.azm.persistent_provider import PersistentAzmProvider
from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.universal_ingester import UniversalAzmIngester, AzmIngestionConfig, AzmConceptDef
from src.brain_core.semantics.mapper import SemanticEvidenceMapper, SemanticEvidenceResult

@pytest.fixture(scope="module")
def real_azm_provider():
    """
    We will use the actual AZM database for these tests since we need to verify against
    the *actual* ShopDeck concepts ingested previously in AZM.
    Wait, the actual AZM DB (AZM_DATABASE_URL) in tests might be empty or sqlite memory.
    Let's inject the actual concepts manually into a temp sqlite DB to ensure test isolation 
    but with realistic schema keys.
    """
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    conn = get_connection(db_url)
    execute_schema(conn)
    
    config = AzmIngestionConfig(
        source_bs="shopdeck",
        namespace_name="shopdeck",
        namespace_classification="EXTERNAL_CHANNEL",
        namespace_description="ShopDeck System",
        contract_version="1.0",
        semantic_contract_content="",
        schematic_contract_content="",
        semantic_source_element="test",
        schematic_source_element="test",
        concepts=[
            AzmConceptDef(
                semantic_key="shopdeck.event.delivery_exception.reason",
                concept_name="Delivery Exception Reason",
                concept_type="ATTRIBUTE",
                definition="NDR Reason",
                source_element="test",
                aliases=["latest_ndr_reason", "reason"]
            ),
            AzmConceptDef(
                semantic_key="shopdeck.metric.ndr_count",
                concept_name="NDR Count",
                concept_type="ATTRIBUTE",
                definition="Number of NDRs",
                source_element="test",
                aliases=["ndr_count", "attempt_count"]
            ),
            AzmConceptDef(
                semantic_key="shopdeck.entity.payment.mode",
                concept_name="Payment Mode",
                concept_type="ATTRIBUTE",
                definition="COD or Prepaid",
                source_element="test",
                aliases=["payment_mode"]
            ),
            AzmConceptDef(
                semantic_key="shopdeck.entity.order.gross_value",
                concept_name="Order Value",
                concept_type="ATTRIBUTE",
                definition="Total amount",
                source_element="test",
                aliases=["order_value", "total_amount"]
            ),
            AzmConceptDef(
                semantic_key="other.concept.ambiguous",
                concept_name="Ambiguous Concept",
                concept_type="ENTITY",
                definition="For testing ambiguity",
                source_element="test",
                aliases=["shared_alias"]
            ),
            AzmConceptDef(
                semantic_key="shopdeck.concept.ambiguous",
                concept_name="Ambiguous Concept 2",
                concept_type="ENTITY",
                definition="For testing ambiguity",
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
    
    provider = PersistentAzmProvider(db_url)
    yield provider
    os.remove(path)


def test_mapper_architectural_boundary(real_azm_provider):
    """
    Test that covers mapping logic, unmapped behavior, ambiguity, 
    and verifies NO interpretation happens.
    """
    mapper = SemanticEvidenceMapper(real_azm_provider)
    
    raw_payload = {
        "latest_ndr_reason": "Customer unavailable",
        "ndr_count": 3,
        "attempt_count": 4, # Should map to the same concept (which triggers collision ambiguity logic in our mapper)
        "payment_mode": "COD",
        "order_value": 1500.0,
        "total_amount": 1500.0, 
        "unknown_key": "some_value",
        "shared_alias": "something",
        "LATEST_NDR_REASON": "Case Normalization Test" # case test
    }
    
    provenance = {
        "source": "exotel",
        "webhook_id": "wh_123"
    }
    
    result = mapper.map_evidence(raw_payload, provenance)
    
    # K. no NDR interpretation
    # C. payment_mode -> existing
    # D. order_value -> existing
    assert "shopdeck.entity.payment.mode" in result.mapped_canonical
    
    # Due to 'latest_ndr_reason' and 'LATEST_NDR_REASON', it collided and went to ambiguous
    assert "shopdeck.event.delivery_exception.reason" in result.ambiguous_physical
    assert "shopdeck.metric.ndr_count" in result.ambiguous_physical # due to ndr_count and attempt_count
    assert "shopdeck.entity.order.gross_value" in result.ambiguous_physical # due to order_value and total_amount
    
def test_clean_mappings(real_azm_provider):
    mapper = SemanticEvidenceMapper(real_azm_provider)
    raw = {
        "latest_ndr_reason": "Customer unavailable",
        "ndr_count": 3,
        "payment_mode": "COD",
        "total_amount": 1500.0,
    }
    prov = {"src": "test"}
    result = mapper.map_evidence(raw, prov)
    
    # A, B, C, D: Mappings
    assert result.mapped_canonical["shopdeck.event.delivery_exception.reason"] == "Customer unavailable"
    assert result.mapped_canonical["shopdeck.metric.ndr_count"] == 3
    assert result.mapped_canonical["shopdeck.entity.payment.mode"] == "COD"
    assert result.mapped_canonical["shopdeck.entity.order.gross_value"] == 1500.0
    
    # H. Values unchanged (Not interpreted to boolean or enum)
    assert result.mapped_canonical["shopdeck.event.delivery_exception.reason"] == "Customer unavailable"
    
    # I. Raw payload preserved
    assert result.original_raw == raw
    # J. Provenance preserved
    assert result.provenance == prov

def test_unknown_key_unmapped(real_azm_provider):
    mapper = SemanticEvidenceMapper(real_azm_provider)
    result = mapper.map_evidence({"unknown_key": 123}, {"src": "test"})
    # E. Unknown key -> UNMAPPED
    assert "unknown_key" in result.unmapped_physical
    assert result.unmapped_physical["unknown_key"] == 123
    assert len(result.mapped_canonical) == 0

def test_shared_alias_ambiguous(real_azm_provider):
    mapper = SemanticEvidenceMapper(real_azm_provider)
    result = mapper.map_evidence({"shared_alias": "val"}, {"src": "test"})
    
    # F. Shared alias -> AMBIGUOUS
    assert "shared_alias" in result.ambiguous_physical
    candidates = result.ambiguous_physical["shared_alias"]["candidate_concepts"]
    assert "other.concept.ambiguous" in candidates
    assert "shopdeck.concept.ambiguous" in candidates
    assert len(result.mapped_canonical) == 0

def test_case_normalization(real_azm_provider):
    mapper = SemanticEvidenceMapper(real_azm_provider)
    # G. Case normalization
    result = mapper.map_evidence({"LaTeSt_nDr_ReAsOn": "val"}, {"src": "test"})
    assert result.mapped_canonical["shopdeck.event.delivery_exception.reason"] == "val"

def test_idempotent_mapping(real_azm_provider):
    mapper = SemanticEvidenceMapper(real_azm_provider)
    raw = {"latest_ndr_reason": "Customer unavailable"}
    prov = {"src": "test"}
    
    # N. Repeated mapping deterministic
    r1 = mapper.map_evidence(raw, prov)
    r2 = mapper.map_evidence(raw, prov)
    assert r1.mapped_canonical == r2.mapped_canonical
    assert r1.unmapped_physical == r2.unmapped_physical
