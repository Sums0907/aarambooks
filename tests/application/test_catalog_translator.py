import pytest
import uuid
from src.application.catalog_translator import CatalogActionTranslator
from src.intelligence_domains.catalog_intelligence.models import ProposedCatalogAction, CatalogIntent, CatalogDraft, DraftField, FieldProvenance
from src.shared.evidence_request_contracts import BusinessStateVerificationResponse, BusinessRealityStatus

class MockCemAdapter:
    async def verify_business_state(self, req):
        if req.verification_target == "product_code" and req.context_payload.get("product_code") == "PC-1":
            return BusinessStateVerificationResponse(
                is_verified=True,
                status=BusinessRealityStatus.ENTITY_RESOLVED,
                evidence_data={"exists": True, "product_internal_id": "00000000-0000-0000-0000-000000000001"}
            )
        return BusinessStateVerificationResponse(is_verified=False, status=BusinessRealityStatus.ENTITY_NOT_FOUND)

@pytest.mark.asyncio
async def test_translator_rejects_unconfirmed():
    adapter = MockCemAdapter()
    translator = CatalogActionTranslator(adapter)
    
    draft = CatalogDraft()
    action = ProposedCatalogAction(intent=CatalogIntent.CREATE_FAMILY, draft=draft, is_confirmed=False)
    
    with pytest.raises(ValueError, match="unconfirmed action"):
        await translator.translate_action(action)

@pytest.mark.asyncio
async def test_translator_rejects_missing_mandatory():
    adapter = MockCemAdapter()
    translator = CatalogActionTranslator(adapter)
    
    draft = CatalogDraft()
    draft.product_code = DraftField(value="PC-1", provenance=FieldProvenance.USER_PROVIDED)
    action = ProposedCatalogAction(intent=CatalogIntent.CREATE_FAMILY, draft=draft, is_confirmed=True)
    
    with pytest.raises(ValueError, match="missing required fields"):
        await translator.translate_action(action)

@pytest.mark.asyncio
async def test_translator_translates_create_family():
    adapter = MockCemAdapter()
    translator = CatalogActionTranslator(adapter)
    
    draft = CatalogDraft()
    draft.product_code = DraftField(value="PC-NEW", provenance=FieldProvenance.USER_PROVIDED)
    draft.product_name = DraftField(value="Name", provenance=FieldProvenance.USER_PROVIDED)
    draft.product_type = DraftField(value="BED", provenance=FieldProvenance.USER_PROVIDED)
    draft.brand = DraftField(value="Aaram", provenance=FieldProvenance.USER_PROVIDED)
    draft.hsn_code = DraftField(value="1234", provenance=FieldProvenance.USER_PROVIDED)
    draft.gst_percentage = DraftField(value="18.0", provenance=FieldProvenance.USER_PROVIDED)
    draft.sku_id = DraftField(value="SKU-NEW", provenance=FieldProvenance.USER_PROVIDED)
    draft.mrp = DraftField(value="1000", provenance=FieldProvenance.USER_PROVIDED)
    draft.selling_price = DraftField(value="800", provenance=FieldProvenance.USER_PROVIDED)
    draft.cost_price = DraftField(value="500", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_length_cm = DraftField(value="10", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_breadth_cm = DraftField(value="10", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_height_cm = DraftField(value="10", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_weight_kg = DraftField(value="1", provenance=FieldProvenance.USER_PROVIDED)
    draft.sku_media_urls = DraftField(value=[], provenance=FieldProvenance.USER_PROVIDED)
    draft.colour = DraftField(value="Red", provenance=FieldProvenance.USER_PROVIDED)
    
    action = ProposedCatalogAction(intent=CatalogIntent.CREATE_FAMILY, draft=draft, is_confirmed=True)
    
    payload = await translator.translate_action(action)
    assert payload.operation == "SaveProductFamily"
    assert payload.product.product_code == "PC-NEW"
    assert payload.product.product_internal_id is None
    assert payload.skus[0].sku_id == "SKU-NEW"
    assert payload.skus[0].sku_internal_id is None

@pytest.mark.asyncio
async def test_translator_resolves_uuids_for_upsert():
    adapter = MockCemAdapter()
    translator = CatalogActionTranslator(adapter)
    
    draft = CatalogDraft()
    draft.product_code = DraftField(value="PC-1", provenance=FieldProvenance.USER_PROVIDED)
    draft.product_name = DraftField(value="Name", provenance=FieldProvenance.USER_PROVIDED)
    draft.product_type = DraftField(value="BED", provenance=FieldProvenance.USER_PROVIDED)
    draft.brand = DraftField(value="Aaram", provenance=FieldProvenance.USER_PROVIDED)
    draft.hsn_code = DraftField(value="1234", provenance=FieldProvenance.USER_PROVIDED)
    draft.gst_percentage = DraftField(value="18.0", provenance=FieldProvenance.USER_PROVIDED)
    draft.sku_id = DraftField(value="SKU-1", provenance=FieldProvenance.USER_PROVIDED)
    draft.mrp = DraftField(value="1000", provenance=FieldProvenance.USER_PROVIDED)
    draft.selling_price = DraftField(value="800", provenance=FieldProvenance.USER_PROVIDED)
    draft.cost_price = DraftField(value="500", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_length_cm = DraftField(value="10", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_breadth_cm = DraftField(value="10", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_height_cm = DraftField(value="10", provenance=FieldProvenance.USER_PROVIDED)
    draft.packaging_weight_kg = DraftField(value="1", provenance=FieldProvenance.USER_PROVIDED)
    draft.sku_media_urls = DraftField(value=[], provenance=FieldProvenance.USER_PROVIDED)
    draft.colour = DraftField(value="Red", provenance=FieldProvenance.USER_PROVIDED)
    
    action = ProposedCatalogAction(intent=CatalogIntent.UPSERT_SKUS, draft=draft, is_confirmed=True)
    
    payload = await translator.translate_action(action)
    assert payload.operation == "SaveProductFamily"
    assert payload.product.product_code == "PC-1"
    assert str(payload.product.product_internal_id) == "00000000-0000-0000-0000-000000000001"
    assert payload.skus[0].sku_id == "SKU-1"

