import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, UTC
from src.workers.brain_normalization_worker import BrainNormalizationWorker
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
import mongomock
from src.infrastructure.adapters.customer_engagement.models import NormalizationStatus
from src.brain_core.semantics.mapper import SemanticEvidenceResult
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
import mongomock_motor

@pytest.mark.asyncio
async def test_zero_writes_to_shopdeck_main_ecosystem():
    mock_db = mongomock_motor.AsyncMongoMockClient().get_database("test")
    
    with patch("src.infrastructure.adapters.customer_engagement.repository.get_mongo_db", new_callable=AsyncMock) as repo_get_db, \
         patch("src.workers.brain_normalization_worker.get_mongo_db", new_callable=AsyncMock) as worker_get_db:
        
        repo_get_db.return_value = mock_db
        worker_get_db.return_value = mock_db
        
        repo = CustomerEngagementRepository()
        
        mock_mapper = MagicMock()
        mock_mapper.map_evidence.return_value = SemanticEvidenceResult(mapped_canonical={"ndr.entity.awb": "AWB_TEST_BOUNDARY"}, unmapped_physical={}, original_raw={}, provenance={})
        
        mock_orch = AsyncMock()
        from enum import Enum
        class MockCat(Enum):
            SELLER_REATTEMPT = "seller_reattempt"
            
        from collections import namedtuple
        DecisionRecommendation = namedtuple('DecisionRecommendation', ['recommended_alternative_id'])
        ExecutionAction = namedtuple('ExecutionAction', ['category', 'parameters', 'reasoning'])
        
        mock_orch.orchestrate_resolution.return_value = (
            DecisionRecommendation(recommended_alternative_id="seller_reattempt"),
            ExecutionAction(category=MockCat.SELLER_REATTEMPT, parameters={}, reasoning="test"),
            "msg"
        )
        
        worker = BrainNormalizationWorker(repo, mock_mapper, mock_orch)
        
        engagement_id = "eng_boundary_test_1"
        await mock_db.customer_engagements.insert_one({
            "engagement_id": engagement_id,
            "status": "COMPLETED",
            "normalization_status": NormalizationStatus.PENDING
        })
        await mock_db.customer_engagement_events.insert_one({
            "engagement_id": engagement_id,
            "provider": "exotel",
            "provider_event_id": "evt_1",
            "raw_payload": {"awb_no": "AWB_TEST_BOUNDARY", "latest_ndr_reason": "Customer unavailable"},
            "occurred_at": datetime.now(UTC)
        })
        
        with patch("httpx.AsyncClient.request") as mock_request:
            processed = await worker.run_one()
            assert processed is True
            
            for call_args in mock_request.call_args_list:
                method, url = call_args[0]
                if method in ["POST", "PUT", "PATCH", "DELETE"]:
                    assert "shopdeck-api" not in str(url), "Found illegal WRITE to real ShopDeck main ecosystem!"
                    
        result = await mock_db.ndr_normalization_results.find_one({"engagement_id": engagement_id})
        assert result is not None
        assert result["recommendation"] == "seller_reattempt"
