import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
import uuid
import os
import tempfile
import pymongo
import mongomock

from src.azm.persistent_provider import PersistentAzmProvider
from src.azm.db import get_connection, execute_schema
from src.azm.ingestion.universal_ingester import UniversalAzmIngester, AzmIngestionConfig, AzmConceptDef
from src.brain_core.semantics.mapper import SemanticEvidenceMapper
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.intelligence_domains.ndr.models import StrategyPatternType
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import NormalizationStatus, EngagementState, CustomerEngagementRecord, CustomerEngagementEvent
from src.workers.brain_normalization_worker import BrainNormalizationWorker

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

@pytest.fixture
def mock_db():
    db = mongomock.MongoClient().db
    # Setup unique index for idempotency test
    db.ndr_normalization_results.create_index(
        [("engagement_id", pymongo.ASCENDING), ("normalization_version", pymongo.ASCENDING)],
        unique=True
    )
    return db

@pytest.fixture
def repo(mock_db):
    repository = CustomerEngagementRepository()
    repository._db = mock_db
    
    # Mock async methods to wrap mongomock
    async def mock_claim():
        return mock_db.customer_engagements.find_one_and_update(
            {
                "status": {"$in": [EngagementState.COMPLETED, EngagementState.FAILED, EngagementState.ESCALATED]},
                "normalization_status": NormalizationStatus.PENDING
            },
            {
                "$set": {
                    "normalization_status": NormalizationStatus.PROCESSING,
                    "updated_at": datetime.now(UTC)
                }
            },
            return_document=pymongo.ReturnDocument.AFTER
        )
        
    async def mock_get_events(eng_id):
        return list(mock_db.customer_engagement_events.find({"engagement_id": eng_id}).sort([
            ("occurred_at", pymongo.ASCENDING),
            ("sequence", pymongo.ASCENDING),
            ("provider_event_id", pymongo.ASCENDING)
        ]))
        
    async def mock_update_status(eng_id, status):
        res = mock_db.customer_engagements.update_one(
            {"engagement_id": eng_id},
            {"$set": {"normalization_status": status, "updated_at": datetime.now(UTC)}}
        )
        return res.modified_count > 0
        
    repository.claim_pending_normalization = mock_claim
    repository.get_engagement_events = mock_get_events
    repository.update_normalization_status = mock_update_status
    
    return repository

@pytest.fixture
def worker(repo, azm_provider, mock_db):
    mapper = SemanticEvidenceMapper(azm_provider)
    
    mock_gateway = AsyncMock()
    mock_knowledge = AsyncMock()
    mock_knowledge.search_knowledge.return_value = []
    mock_memory = AsyncMock()
    mock_memory.read_memory.return_value = []
    mock_memory.write_memory.return_value = None

    orchestrator = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=mock_knowledge,
        memory=mock_memory
    )
    
    w = BrainNormalizationWorker(
        engagement_repo=repo,
        semantic_mapper=mapper,
        ndr_orchestrator=orchestrator
    )
    
    # Mock db for ndr_normalization_results insertion
    async def async_get_db():
        class AsyncDB:
            def __init__(self, mdb):
                self.mdb = mdb
                
            @property
            def ndr_normalization_results(self):
                class AsyncResults:
                    async def insert_one(self, doc):
                        return mock_db.ndr_normalization_results.insert_one(doc)
                return AsyncResults()
        return AsyncDB(mock_db)
        
    w._get_db = async_get_db
    return w

@pytest.mark.asyncio
async def test_atomic_claim_terminal_pending(worker, repo, mock_db):
    """A. COMPLETED + PENDING claim."""
    engagement_id = "eng_1"
    mock_db.customer_engagements.insert_one({
        "engagement_id": engagement_id,
        "status": EngagementState.COMPLETED,
        "normalization_status": NormalizationStatus.PENDING
    })
    
    # Need events so it doesn't fail right away
    mock_db.customer_engagement_events.insert_one({
        "engagement_id": engagement_id,
        "provider": "exotel",
        "provider_event_id": "evt_1",
        "raw_payload": {"awb_no": "AWB_DEL_7788", "latest_ndr_reason": "Customer unavailable"},
        "occurred_at": datetime.now(UTC)
    })
    
    processed = await worker.run_one()
    assert processed is True
    
    # Check states
    eng = mock_db.customer_engagements.find_one({"engagement_id": engagement_id})
    assert eng["normalization_status"] == NormalizationStatus.COMPLETED.value
    
    result = mock_db.ndr_normalization_results.find_one({"engagement_id": engagement_id})
    assert result is not None
    assert result["recommendation"] == StrategyPatternType.AUTONOMOUS_RESCHEDULE.value
    assert result["authorized_action"] == "suggested_resolution"

@pytest.mark.asyncio
async def test_non_terminal_engagement_ignored(worker, repo, mock_db):
    """D. Non-terminal engagement is ignored."""
    mock_db.customer_engagements.insert_one({
        "engagement_id": "eng_2",
        "status": EngagementState.IN_PROGRESS,
        "normalization_status": NormalizationStatus.PENDING
    })
    
    processed = await worker.run_one()
    assert processed is False

@pytest.mark.asyncio
async def test_duplicate_invocation_idempotent(worker, mock_db):
    """AA. Duplicate invocation is idempotent. (engagement_id, normalization_version)"""
    mock_db.customer_engagements.insert_one({
        "engagement_id": "eng_3",
        "status": EngagementState.COMPLETED,
        "normalization_status": NormalizationStatus.PENDING,
        "normalization_version": 1
    })
    
    mock_db.customer_engagement_events.insert_one({
        "engagement_id": "eng_3",
        "raw_payload": {"awb_no": "AWB_DEL_7788"},
        "occurred_at": datetime.now(UTC)
    })
    
    # Run first time -> creates result
    await worker.run_one()
    assert mock_db.ndr_normalization_results.count_documents({"engagement_id": "eng_3"}) == 1
    
    # Reset status to pending to simulate retry
    mock_db.customer_engagements.update_one(
        {"engagement_id": "eng_3"}, 
        {"$set": {"normalization_status": NormalizationStatus.PENDING}}
    )
    
    # Run second time -> should hit duplicate key error and catch it, returning True and setting to COMPLETED
    processed = await worker.run_one()
    assert processed is True
    assert mock_db.ndr_normalization_results.count_documents({"engagement_id": "eng_3"}) == 1
