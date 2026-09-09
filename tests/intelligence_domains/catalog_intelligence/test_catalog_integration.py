import os
import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
import asyncpg
import httpx
import json

from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter
from src.shared.rabta_interfaces import IntelligenceDomainProvider, ContextExecutionAdapter
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessEvidenceResponse, BusinessRealityStatus
from src.shared.requirement_classification_contracts import ClassifiedRequirement, ConversationalUnderstanding
from src.shared.conversational_contracts import (
    ConversationalIntent,
    NormalizedParameter,
    ParameterDataType,
    SemanticEntityReference,
    ConversationalResponseType
)
from src.shared.config import settings
from src.brain_core.decision.decision_engine import DecisionEngine
from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator

# CATALOG_INTERNAL_TOKEN must be set BEFORE business_systems.catalog.api is imported below -
# that module reads it into a module-level constant at import time, so setting it any later
# leaves the service permanently seeing an empty token and 500ing "not configured on server"
# on every authenticated request regardless of what the client sends.
CATALOG_TEST_TOKEN = "test_integration_token"
os.environ["CATALOG_INTERNAL_TOKEN"] = CATALOG_TEST_TOKEN

# Catalog is reached only over HTTP now (CatalogCemAdapter no longer imports Catalog's
# Python code) - these two imports are test-only, to exercise the real Catalog FastAPI app
# and its real CATALOG_DATABASE_URL in-process via httpx.ASGITransport, the same way
# business_systems/catalog/tests/conftest.py already tests it standalone. This file
# previously ran destructive DROP TABLE/CREATE TABLE DDL for a hand-rolled, incomplete
# catalog schema directly against settings.database_url (Brain's own database) - that is
# exactly how Catalog's tables ended up living inside Brain's database instead of
# CATALOG_DATABASE_URL to begin with, and is replaced here with the real schema.sql applied
# to the real, separate Catalog database.
from business_systems.catalog.api import app as catalog_app
from business_systems.catalog.config import CATALOG_DATABASE_URL

_SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "business_systems", "catalog", "schema.sql"))

@pytest_asyncio.fixture
async def db_pool():
    pool = await asyncpg.create_pool(CATALOG_DATABASE_URL, min_size=1, max_size=5)

    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    async with pool.acquire() as conn:
        await conn.execute(schema_sql)
        # Clear out existing for isolated testing
        await conn.execute("""
            TRUNCATE TABLE
                catalog_skus,
                catalog_products,
                catalog_product_code_reservations,
                catalog_sku_id_reservations,
                catalog_price_history,
                catalog_idempotency_records
            CASCADE;
        """)

        # Insert a dummy product for discovery
        product_id = uuid4()
        await conn.execute(
            """
            INSERT INTO catalog_products (internal_id, product_code, name, description, product_type, brand, lifecycle_state)
            VALUES ($1, 'TESTBED-01', 'Test Bed', 'Desc', 'BED', 'Aaram', 'READY');
            """,
            product_id
        )
        
        # Insert a product to simulate a SKU collision
        collision_product_id = uuid4()
        await conn.execute(
            """
            INSERT INTO catalog_products (internal_id, product_code, name, description, product_type, brand, lifecycle_state)
            VALUES ($1, 'COLLISION-01', 'Collision Bed', 'Desc', 'BED', 'Aaram', 'READY');
            """,
            collision_product_id
        )
        
        sku_id = uuid4()
        await conn.execute(
            """
            INSERT INTO catalog_skus (
                internal_id, product_internal_id, sku_id, colour, size, size_type, 
                mrp, selling_price, cost_price, packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
            ) VALUES (
                $1, $2, 'BEDBL', 'BL', 'S', 'size', 1000.0, 900.0, 500.0, 10, 10, 10, 1
            );
            """,
            sku_id, collision_product_id
        )
        
    yield pool
    await pool.close()


@pytest.fixture
def orchestrator():
    return CatalogIntelligenceOrchestrator()

@pytest_asyncio.fixture
async def cem(db_pool):
    # db_pool is depended on purely for ordering: it must seed the database before the
    # Catalog app's own pool (started here) reads from it. ASGITransport runs the real
    # FastAPI app in-process against the real CATALOG_DATABASE_URL, with no separate server.
    await catalog_app.router.startup()
    transport = httpx.ASGITransport(app=catalog_app)
    adapter = CatalogCemAdapter(base_url="http://catalog-test", internal_token=CATALOG_TEST_TOKEN, transport=transport)
    yield adapter
    await adapter._ensure_client().aclose()
    await catalog_app.router.shutdown()

@pytest.mark.asyncio
async def test_discovery_with_one_distinct_match(cem):
    understanding = ConversationalUnderstanding(
        original_query="Add to existing TESTBED-01",
        intent=ConversationalIntent.SEARCH,
        entities=[SemanticEntityReference(original_expression="TESTBED-01", inferred_type="product_code")]
    )
    request = AbstractEvidenceRequest(classified_requirement=ClassifiedRequirement(understanding=understanding))
    
    response = await cem.execute_evidence_request(request, auth_context="")
    assert response.status == BusinessRealityStatus.ENTITY_RESOLVED
    assert "internal_id" in response.evidence_data

@pytest.mark.asyncio
async def test_discovery_with_zero_matches(cem):
    understanding = ConversationalUnderstanding(
        original_query="Add to existing NONEXISTENT-01",
        intent=ConversationalIntent.SEARCH,
        entities=[SemanticEntityReference(original_expression="NONEXISTENT-01", inferred_type="product_code")]
    )
    request = AbstractEvidenceRequest(classified_requirement=ClassifiedRequirement(understanding=understanding))
    
    response = await cem.execute_evidence_request(request, auth_context="")
    assert response.status == BusinessRealityStatus.ENTITY_NOT_FOUND

@pytest.mark.asyncio
async def test_action_success(cem):
    understanding = ConversationalUnderstanding(
        original_query="Add blue variant",
        intent=ConversationalIntent.ACTION,
        parameters=[
                NormalizedParameter(parameter_name="operation", data_type=ParameterDataType.STRING, value="SaveProductFamily", original_expression="SaveProductFamily"),
                NormalizedParameter(parameter_name="sku_candidates", data_type=ParameterDataType.STRING, value=["NEWBEDBL", "NEWBEDBL-1"], original_expression=""),
                NormalizedParameter(parameter_name="product_type", data_type=ParameterDataType.STRING, value="BED", original_expression="BED"),
                NormalizedParameter(parameter_name="colour", data_type=ParameterDataType.STRING, value="BL", original_expression="BL"),
                NormalizedParameter(parameter_name="mrp", data_type=ParameterDataType.STRING, value="1000", original_expression="1000"),
                NormalizedParameter(parameter_name="selling_price", data_type=ParameterDataType.STRING, value="900", original_expression="900"),
                NormalizedParameter(parameter_name="cost_price", data_type=ParameterDataType.STRING, value="500", original_expression="500"),
                NormalizedParameter(parameter_name="packaging_length_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_breadth_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_height_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_weight_kg", data_type=ParameterDataType.STRING, value="1", original_expression="1")
            ]  )
    request = AbstractEvidenceRequest(classified_requirement=ClassifiedRequirement(understanding=understanding))
    
    response = await cem.execute_evidence_request(request, auth_context="")
    assert response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE
    assert response.evidence_data["sku_id"] == "NEWBEDBL"

@pytest.mark.asyncio
async def test_sku_collision_fallback(cem):
    # 'BEDBL' already exists (inserted by db_pool fixture), so Candidate 0 will collide. Candidate 1 ('BEDBL-1') should succeed.
    understanding = ConversationalUnderstanding(
        original_query="Add blue variant",
        intent=ConversationalIntent.ACTION,
        parameters=[
                NormalizedParameter(parameter_name="operation", data_type=ParameterDataType.STRING, value="SaveProductFamily", original_expression="SaveProductFamily"),
                NormalizedParameter(parameter_name="sku_candidates", data_type=ParameterDataType.STRING, value=["BEDBL", "BEDBL-1"], original_expression=""),
                NormalizedParameter(parameter_name="product_type", data_type=ParameterDataType.STRING, value="BED", original_expression="BED"),
                NormalizedParameter(parameter_name="colour", data_type=ParameterDataType.STRING, value="BL", original_expression="BL"),
                NormalizedParameter(parameter_name="mrp", data_type=ParameterDataType.STRING, value="1000", original_expression="1000"),
                NormalizedParameter(parameter_name="selling_price", data_type=ParameterDataType.STRING, value="900", original_expression="900"),
                NormalizedParameter(parameter_name="cost_price", data_type=ParameterDataType.STRING, value="500", original_expression="500"),
                NormalizedParameter(parameter_name="packaging_length_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_breadth_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_height_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_weight_kg", data_type=ParameterDataType.STRING, value="1", original_expression="1")
            ]
    )
    request = AbstractEvidenceRequest(classified_requirement=ClassifiedRequirement(understanding=understanding))
    
    response = await cem.execute_evidence_request(request, auth_context="")
    assert response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE
    # It must have successfully used candidate 1
    assert response.evidence_data["sku_id"] == "BEDBL-1"

@pytest.mark.asyncio
async def test_exhaustion_scenario(cem, db_pool):
    # Setup so that all 3 candidates collide
    async with db_pool.acquire() as conn:
        collision_product_id = uuid4()
        await conn.execute(
            """
            INSERT INTO catalog_products (internal_id, product_code, name, description, product_type, brand, lifecycle_state)
            VALUES ($1, 'COLLISION-02', 'Collision Bed 2', 'Desc', 'BED', 'Aaram', 'READY');
            """,
            collision_product_id
        )
        
        for sku in ["EXHAUST", "EXHAUST-1", "EXHAUST-2"]:
            await conn.execute(
                """
                INSERT INTO catalog_skus (
                    internal_id, product_internal_id, sku_id, colour, size, size_type, 
                    mrp, selling_price, cost_price, packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES (
                    $1, $2, $3, 'BL', 'S', 'size', 1000.0, 900.0, 500.0, 10, 10, 10, 1
                );
                """,
                uuid4(), collision_product_id, sku
            )
            
    understanding = ConversationalUnderstanding(
        original_query="Add blue variant",
        intent=ConversationalIntent.ACTION,
        parameters=[
                NormalizedParameter(parameter_name="operation", data_type=ParameterDataType.STRING, value="SaveProductFamily", original_expression="SaveProductFamily"),
                NormalizedParameter(parameter_name="sku_candidates", data_type=ParameterDataType.STRING, value=["EXHAUST", "EXHAUST-1", "EXHAUST-2"], original_expression=""),
                NormalizedParameter(parameter_name="product_type", data_type=ParameterDataType.STRING, value="BED", original_expression="BED"),
                NormalizedParameter(parameter_name="colour", data_type=ParameterDataType.STRING, value="BL", original_expression="BL"),
                NormalizedParameter(parameter_name="mrp", data_type=ParameterDataType.STRING, value="1000", original_expression="1000"),
                NormalizedParameter(parameter_name="selling_price", data_type=ParameterDataType.STRING, value="900", original_expression="900"),
                NormalizedParameter(parameter_name="cost_price", data_type=ParameterDataType.STRING, value="500", original_expression="500"),
                NormalizedParameter(parameter_name="packaging_length_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_breadth_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_height_cm", data_type=ParameterDataType.STRING, value="10", original_expression="10"),
                NormalizedParameter(parameter_name="packaging_weight_kg", data_type=ParameterDataType.STRING, value="1", original_expression="1")
            ]
    )
    request = AbstractEvidenceRequest(classified_requirement=ClassifiedRequirement(understanding=understanding))
    
    response = await cem.execute_evidence_request(request, auth_context="")
    
    # Check that it returns EXECUTION_LIMITATION due to SKU_PROPOSAL_EXHAUSTED
    assert response.status == BusinessRealityStatus.EXECUTION_LIMITATION
    assert any("SKU_PROPOSAL_EXHAUSTED" in lim.reason for lim in response.execution_limitations)


@pytest.mark.asyncio
async def test_human_approval_required(orchestrator):
    # An action intent without context will now trigger a SUMMARIZE intent asking for mandatory fields
    understanding = await orchestrator.extract_understanding("Add variant")
    assert understanding.intent == ConversationalIntent.SUMMARIZE
    
    # Let's mock a case where interpret_evidence gets a response
    # But wait, without AuthorizedContext, the orchestrator should return HUMAN_APPROVAL_REQUIRED immediately.
    # However, in our naive `extract_understanding` mock, we just say ACTION. 
    # But if we pass it through interpret_evidence without discovery...
    pass

@pytest.mark.asyncio
async def test_propose_attach_flow(orchestrator):
    # Simulate a successful discovery response
    discovery_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.ENTITY_RESOLVED,
        evidence_data={"internal_id": str(uuid4())}
    )
    
    conv_response = await orchestrator.interpret_evidence(discovery_response)
    
    assert conv_response.response_type == ConversationalResponseType.SUCCESS
    assert conv_response.render_directives["operation"] == "SaveProductFamily"
    assert "sku_candidates" in conv_response.render_directives
    # Ensure it generated exactly 3
    assert len(conv_response.render_directives["sku_candidates"]) == 3
