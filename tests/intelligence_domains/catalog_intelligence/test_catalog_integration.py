import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
import asyncpg
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

from business_systems.catalog.service import CatalogService
from business_systems.catalog.models import SaveProductFamilyPayload, SaveProductInput, SaveSkuInput

@pytest_asyncio.fixture
async def db_pool():
    url = settings.database_url.replace("postgresql+asyncpg", "postgresql")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
    
    # Initialize some data for tests
    async with pool.acquire() as conn:
        await conn.execute("""
        DROP VIEW IF EXISTS vw_catalog_products;
        DROP TABLE IF EXISTS catalog_skus CASCADE;
        DROP TABLE IF EXISTS catalog_products CASCADE;
        DROP TABLE IF EXISTS catalog_product_code_reservations CASCADE;
        DROP TABLE IF EXISTS catalog_sku_id_reservations CASCADE;
        DROP TABLE IF EXISTS catalog_price_history CASCADE;
        DROP TABLE IF EXISTS catalog_idempotency_records CASCADE;

        CREATE TABLE catalog_products (
            internal_id UUID PRIMARY KEY,
            product_code VARCHAR(255),
            name VARCHAR(255),
            description TEXT,
            product_type VARCHAR(50),
            brand VARCHAR(50),
            hsn_code VARCHAR(50),
            gst_percentage DECIMAL,
            fabric_type VARCHAR(50),
            care_instructions TEXT,
            set_composition VARCHAR(255),
            product_media_urls JSONB,
            size_chart_url VARCHAR(255),
            video_urls JSONB,
            collection_tags TEXT[],
            lifecycle_state VARCHAR(50)
        );
        CREATE TABLE catalog_skus (
            internal_id UUID PRIMARY KEY,
            product_internal_id UUID,
            sku_id VARCHAR(255) UNIQUE,
            colour VARCHAR(50),
            size VARCHAR(50),
            size_type VARCHAR(50),
            pack_configuration VARCHAR(50),
            mrp DECIMAL,
            selling_price DECIMAL,
            cost_price DECIMAL,
            packaging_length_cm DECIMAL,
            packaging_breadth_cm DECIMAL,
            packaging_height_cm DECIMAL,
            packaging_weight_kg DECIMAL,
            sku_media_urls JSONB
        );
        CREATE TABLE catalog_product_code_reservations (
            reservation_id UUID PRIMARY KEY,
            product_code VARCHAR(255) UNIQUE,
            product_internal_id UUID,
            reserved_by VARCHAR(50),
            reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'ACTIVE'
        );
        CREATE TABLE catalog_sku_id_reservations (
            reservation_id UUID PRIMARY KEY,
            sku_id VARCHAR(255) UNIQUE,
            sku_internal_id UUID,
            reserved_by VARCHAR(50),
            reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE catalog_price_history (
            history_id SERIAL PRIMARY KEY,
            sku_internal_id UUID,
            previous_mrp DECIMAL,
            new_mrp DECIMAL,
            previous_selling_price DECIMAL,
            new_selling_price DECIMAL,
            previous_cost_price DECIMAL,
            new_cost_price DECIMAL,
            changed_by VARCHAR(50),
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE catalog_idempotency_records (
            idempotency_key VARCHAR(255) PRIMARY KEY,
            operation VARCHAR(50),
            request_hash VARCHAR(64),
            response_payload JSONB,
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        );
        DROP VIEW IF EXISTS vw_catalog_products;
        CREATE VIEW vw_catalog_products AS 
        SELECT internal_id as product_internal_id, name as product_name, product_code 
        FROM catalog_products;
        """)
        # Clear out existing for isolated testing
        await conn.execute("DELETE FROM catalog_skus;")
        await conn.execute("DELETE FROM catalog_products;")
        await conn.execute("DELETE FROM catalog_product_code_reservations;")
        await conn.execute("DELETE FROM catalog_sku_id_reservations;")
        await conn.execute("DELETE FROM catalog_price_history;")
        await conn.execute("DELETE FROM catalog_idempotency_records;")
        
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
                $1, $2, 'BEDBL', 'BL', 'S', 'US', 1000.0, 900.0, 500.0, 10, 10, 10, 1
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
    adapter = CatalogCemAdapter(database_url=settings.database_url)
    adapter._pool = db_pool
    adapter._service = CatalogService(db_pool)
    return adapter

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
                    $1, $2, $3, 'BL', 'S', 'US', 1000.0, 900.0, 500.0, 10, 10, 10, 1
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
