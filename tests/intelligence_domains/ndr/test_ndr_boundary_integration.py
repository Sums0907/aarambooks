import pytest
from unittest.mock import AsyncMock
from datetime import datetime, UTC
import uuid
import os
import tempfile

from src.azm.persistent_provider import PersistentAzmProvider
from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.universal_ingester import UniversalAzmIngester, AzmIngestionConfig, AzmConceptDef
from src.brain_core.semantics.mapper import SemanticEvidenceMapper, SemanticEvidenceResult
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.knowledge.interfaces import KnowledgeProvider
from src.brain_core.memory.interfaces import MemoryProvider
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata
from src.intelligence_domains.ndr.models import StrategyPatternType

@pytest.fixture(scope="module")
def azm_provider():
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
                semantic_key="ndr.entity.awb",
                concept_name="AWB Number",
                concept_type="ENTITY",
                definition="Air Waybill Tracking Number",
                source_element="test",
                aliases=["awb_no", "awb"]
            ),
            AzmConceptDef(
                semantic_key="ndr.entity.customer_id",
                concept_name="Customer ID",
                concept_type="ENTITY",
                definition="Customer ID",
                source_element="test",
                aliases=["customer_id"]
            ),
            AzmConceptDef(
                semantic_key="ndr.entity.customer",
                concept_name="Customer Name",
                concept_type="ENTITY",
                definition="Customer Name",
                source_element="test",
                aliases=["customer_name"]
            ),
            AzmConceptDef(
                semantic_key="ndr.entity.courier_partner",
                concept_name="Courier Partner",
                concept_type="ENTITY",
                definition="Courier Partner",
                source_element="test",
                aliases=["courier_partner"]
            )
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


@pytest.mark.asyncio
async def test_end_to_end_boundary(azm_provider):
    """
    Test the complete integration boundary:
    raw physical evidence -> SemanticEvidenceMapper -> canonical EvidenceItems -> NDRIntelligenceOrchestrator
    """
    # 1. Raw Event 1 (Webhook creation)
    raw_event_1 = {
        "awb_no": "AWB_DEL_7788",
        "customer_id": "cust_456",
        "customer_name": "Rahul Verma",
        "courier_partner": "Delhivery",
        "order_value": 1850.0,
        "payment_mode": "cod",
        "attempt_count": 1,
        "latest_ndr_reason": "Customer unavailable / door locked"
    }

    # 2. Raw Event 2 (Transcript insights arriving later)
    raw_event_2 = {
        "customer.attribute.phone": "+919876543210", # derived
        "customer.attribute.preferred_date": "2026-09-04", # derived
        "customer.state.intent": "PENDING_CONTACT", # derived
        "customer.state.sentiment": "NEUTRAL" # derived
    }

    mapper = SemanticEvidenceMapper(azm_provider)

    mapped_result_1 = mapper.map_evidence(raw_event_1, {"source": "webhook"})
    mapped_result_2 = mapper.map_evidence(raw_event_2, {"source": "transcript"})

    # Ensure physical keys were mapped canonically (e.g. latest_ndr_reason -> shopdeck.event.delivery_exception.reason)
    assert "shopdeck.event.delivery_exception.reason" in mapped_result_1.mapped_canonical

    evidence_pkg = EvidencePackage(
        package_id=str(uuid.uuid4()),
        plan_id=str(uuid.uuid4()),
        sufficiency_assessment="SUFFICIENT",
        evidence_items=[
            EvidenceItem(
                item_id=str(uuid.uuid4()),
                semantic_identity="ndr.event_payload",
                data_payload=mapped_result_1.mapped_canonical,
                provenance=ProvenanceMetadata(source_system="webhook", retrieval_timestamp=datetime.now(UTC))
            ),
            EvidenceItem(
                item_id=str(uuid.uuid4()),
                semantic_identity="ndr.event_payload",
                data_payload=mapped_result_2.unmapped_physical, # derived intents are passed as unmapped in this test since they aren't in AZM mock
                provenance=ProvenanceMetadata(source_system="transcript", retrieval_timestamp=datetime.now(UTC))
            )
        ]
    )

    # 3. NDR Intelligence Orchestrator (with canonical evidence)
    mock_gateway = AsyncMock()
    mock_knowledge = AsyncMock(spec=KnowledgeProvider)
    mock_knowledge.search_knowledge.return_value = []
    mock_memory = AsyncMock(spec=MemoryProvider)
    mock_memory.read_memory.return_value = []
    mock_memory.write_memory.return_value = None

    orchestrator = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=mock_knowledge,
        memory=mock_memory
    )

    decision, action, customer_message = await orchestrator.orchestrate_resolution(evidence_pkg)

    # 4. Assertions on NDR result
    assert decision.recommended_alternative_id == StrategyPatternType.AUTONOMOUS_RESCHEDULE.value
    assert action.parameters.get("reattempt_date") == "2026-09-04"
    assert "2026-09-04" in customer_message
