import asyncio
import json
import uuid

from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
from src.shared.conversational_contracts import MultimodalQuery
from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter
from src.application.catalog_translator import CatalogActionTranslator
from business_systems.catalog.service import CatalogService
from src.intelligence_domains.catalog_intelligence.models import ProposedCatalogAction, FieldProvenance

class DummyKnowledge:
    async def get_namespace_schema(self, namespace):
        return {}
    async def retrieve_evidence(self, *args, **kwargs):
        return []
    async def get_evidence(self, id):
        class Ev:
            def __init__(self):
                self.id = "sabaq-id-123"
        return Ev()

class DummyGateway:
    async def generate(self, request):
        class Resp:
            content = json.dumps({
                "operation_intent": "CREATE_FAMILY",
                "draft_fields": {
                    "product_code": {"value": "PC-MB-1"},
                    "product_name": {"value": "Midnight Blue Bedsheet"},
                    "product_type": {"value": "BED"},
                    "brand": {"value": "Aaram"},
                    "hsn_code": {"value": "6304"},
                    "gst_percentage": {"value": "12.0"},
                    "sku_id": {"value": "SKU-MB-K"},
                    "colour": {"value": "Midnight Blue"},
                    "size": {"value": "King Size"},
                    "mrp": {"value": "2999", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "selling_price": {"value": "1499", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "cost_price": {"value": "700", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "packaging_length_cm": {"value": "30", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "packaging_breadth_cm": {"value": "25", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "packaging_height_cm": {"value": "10", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "packaging_weight_kg": {"value": "1.5", "candidate_sabaq_reference_id": "sabaq-id-123"},
                    "sku_media_urls": {"value": []}
                }
            })
        return Resp()

async def run_e2e():
    import os
    os.environ["POSTGRES_DB"] = "aarambooks_test"
    from src.shared.config import settings
    db_url = settings.database_url
    
    knowledge = DummyKnowledge()
    gateway = DummyGateway()
    cem_adapter = CatalogCemAdapter(database_url=db_url)
    
    await cem_adapter._ensure_initialized()
    async with cem_adapter._pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS catalog_skus CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_products CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_price_history CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_idempotency_records CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_product_code_reservations CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_sku_id_reservations CASCADE;")
        
        with open("business_systems/catalog/schema.sql", "r") as f:
            schema = f.read()
        await conn.execute(schema)

    class MockCemResolver:
        def resolve(self, domain):
            return cem_adapter
            
    orchestrator = CatalogIntelligenceOrchestrator(
        memory_provider=None,
        azm_provider=knowledge,
        sabaq_provider=knowledge,
        gateway_provider=gateway,
        cem_resolver=MockCemResolver()
    )
    
    query = MultimodalQuery(text="Add Midnight Blue bedsheet, King size, ₹1499 selling price, cost ₹700.")
    understanding = await orchestrator.extract_understanding(query)
    
    action_json = None
    for p in understanding.parameters:
        if p.parameter_name == "action_json":
            action_json = p.value
            
    assert action_json is not None
    action = ProposedCatalogAction.model_validate_json(action_json)
    
    translator = CatalogActionTranslator(cem_adapter)
    try:
        await translator.translate_action(action)
        assert False, "Should have rejected unconfirmed action"
    except ValueError as e:
        assert "unconfirmed action" in str(e)
        
    action.is_confirmed = True

    action.draft.mrp.value = "2999"
    action.draft.selling_price.value = "1499"
    action.draft.cost_price.value = "700"
    action.draft.packaging_length_cm.value = "30"
    action.draft.packaging_breadth_cm.value = "25"
    action.draft.packaging_height_cm.value = "10"
    action.draft.packaging_weight_kg.value = "1.5"
    
    for field_name in action.draft.model_fields:
        field = getattr(action.draft, field_name)
        if field and hasattr(field, "provenance"):
            field.provenance = FieldProvenance.USER_PROVIDED
    
    payload = await translator.translate_action(action)
    
    response = await cem_adapter._service.save_product_family(payload)
    
    assert response.status == "SUCCESS"
    assert response.product_code == "PC-MB-1"
    
    async with cem_adapter._pool.acquire() as conn:
        prod = await conn.fetchrow("SELECT * FROM catalog_products WHERE product_code = $1", "PC-MB-1")
        assert prod is not None
        assert prod["name"] == "Midnight Blue Bedsheet"
        
        sku = await conn.fetchrow("SELECT * FROM catalog_skus WHERE product_internal_id = $1", prod["internal_id"])
        assert sku is not None
        assert sku["sku_id"] == "SKU-MB-K"
        assert float(sku["selling_price"]) == 1499.0
        
    print("END-TO-END BUSINESS VALUE TEST PASSED!")
    await cem_adapter._service.close()

if __name__ == '__main__':
    asyncio.run(run_e2e())
