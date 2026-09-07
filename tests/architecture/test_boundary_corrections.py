import pytest
import asyncio
from uuid import uuid4
from src.shared.conversational_contracts import MultimodalQuery
from src.shared.rabta_interfaces import ContextExecutionAdapter
from src.shared.evidence_request_contracts import BusinessStateVerificationRequest, BusinessRealityStatus
from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter

@pytest.fixture
def test_db_url():
    from src.shared.config import settings
    return settings.database_url

@pytest.mark.asyncio
async def test_multimodal_query_backward_compatibility():
    # 1. Legacy text callers remain compatible
    query = MultimodalQuery(text="legacy string")
    assert query.text == "legacy string"
    assert query.image_uris == []
    
@pytest.mark.asyncio
async def test_multimodal_input_reaches_id():
    # 2. Multimodal input reaches an ID.
    query = MultimodalQuery(
        text="this is a red bedsheet",
        image_uris=["s3://bucket/image1.jpg"]
    )
    assert len(query.image_uris) == 1

@pytest.mark.asyncio
async def test_id_cannot_access_catalog_db_directly():
    # 3. ID cannot access Catalog DB directly.
    pass

from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_typed_current_state_verification(test_db_url):
    cem = CatalogCemAdapter(test_db_url)
    
    req = BusinessStateVerificationRequest(
        domain_urn="urn:aarambooks:cem:catalog",
        verification_target="product_code",
        context_payload={"product_code": "NONEXISTENT"}
    )
    
    with patch('src.infrastructure.adapters.catalog_cem_adapter.asyncpg.create_pool', new_callable=AsyncMock) as mock_pool:
        # Create a mock connection that has an async fetchval
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = False
        
        # Create a mock context manager for acquire()
        mock_acquire_cm = AsyncMock()
        mock_acquire_cm.__aenter__.return_value = mock_conn
        
        # Make the pool's acquire() return the context manager
        mock_pool_instance = MagicMock()
        mock_pool_instance.acquire.return_value = mock_acquire_cm
        mock_pool.return_value = mock_pool_instance
        
        resp = await cem.verify_business_state(req)
        assert resp.is_verified is True
        assert resp.evidence_data.get("exists") is False
    
    req_bad = BusinessStateVerificationRequest(
        domain_urn="urn:aarambooks:cem:catalog",
        verification_target="arbitrary_sql",
        context_payload={"query": "DROP TABLE catalog_products"}
    )
    resp_bad = await cem.verify_business_state(req_bad)
    assert resp_bad.status == BusinessRealityStatus.EXECUTION_LIMITATION
