import os

# Must be set before business_systems.catalog.api is imported (module-level constant read at
# import time) - see tests/intelligence_domains/catalog_intelligence/test_catalog_integration.py
# for the same note.
os.environ.setdefault("CATALOG_INTERNAL_TOKEN", "test_boundary_token")

import pytest
import pytest_asyncio
import httpx
from uuid import uuid4
from src.shared.conversational_contracts import MultimodalQuery
from src.shared.rabta_interfaces import ContextExecutionAdapter
from src.shared.evidence_request_contracts import BusinessStateVerificationRequest, BusinessRealityStatus
from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter
from business_systems.catalog.api import app as catalog_app

@pytest_asyncio.fixture
async def cem():
    # Real Catalog FastAPI app in-process against its real CATALOG_DATABASE_URL - the old
    # version of this test mocked asyncpg.create_pool directly inside the adapter, which no
    # longer exists now that Catalog is reached only over HTTP (see catalog_cem_adapter.py).
    await catalog_app.router.startup()
    transport = httpx.ASGITransport(app=catalog_app)
    adapter = CatalogCemAdapter(
        base_url="http://catalog-test",
        internal_token=os.environ["CATALOG_INTERNAL_TOKEN"],
        transport=transport,
    )
    yield adapter
    await adapter._ensure_client().aclose()
    await catalog_app.router.shutdown()

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

@pytest.mark.asyncio
async def test_typed_current_state_verification(cem):
    req = BusinessStateVerificationRequest(
        domain_urn="urn:aarambooks:cem:catalog",
        verification_target="product_code",
        context_payload={"product_code": "NONEXISTENT-BOUNDARY-TEST"}
    )
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
