import uuid
from typing import Dict, Any, List, Optional
from business_systems.catalog.models import SaveProductFamilyPayload, SaveProductInput, SaveSkuInput
from src.intelligence_domains.catalog_intelligence.models import ProposedCatalogAction, CatalogIntent, FieldProvenance
from src.shared.evidence_request_contracts import BusinessStateVerificationRequest
from src.shared.rabta_interfaces import ContextExecutionAdapter

class CatalogActionTranslator:
    def __init__(self, cem_adapter: ContextExecutionAdapter):
        self._cem_adapter = cem_adapter

    async def translate_action(self, action: ProposedCatalogAction) -> SaveProductFamilyPayload:
        if not action.is_confirmed:
            raise ValueError("Cannot translate an unconfirmed action.")

        missing = action.draft.get_missing_mandatory_fields()
        if missing:
            raise ValueError(f"Action draft is missing required fields: {missing}")

        draft = action.draft
        
        p_code_field = draft.product_code
        sku_id_field = draft.sku_id
        
        if not p_code_field or not p_code_field.value or p_code_field.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER:
            raise ValueError("product_code is required.")
        if not sku_id_field or not sku_id_field.value or sku_id_field.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER:
            raise ValueError("sku_id is required.")
            
        p_code = p_code_field.value
        s_id = sku_id_field.value

        product_internal_id = None
        sku_internal_id = None

        if action.intent == CatalogIntent.UPSERT_SKUS:
            p_req = BusinessStateVerificationRequest(
                domain_urn="urn:aarambooks:cem:catalog",
                verification_target="product_code",
                context_payload={"product_code": p_code}
            )
            p_resp = await self._cem_adapter.verify_business_state(p_req)
            if p_resp.is_verified and p_resp.evidence_data and p_resp.evidence_data.get("exists"):
                product_internal_id = uuid.UUID(p_resp.evidence_data["product_internal_id"])
            else:
                raise ValueError(f"UPSERT_SKUS intent requires an existing product family for code {p_code}.")

        def val(field):
            return field.value if field and field.provenance != FieldProvenance.UNKNOWN_REQUIRES_USER else None

        prod_in = SaveProductInput(
            product_internal_id=product_internal_id,
            product_code=p_code,
            name=val(draft.product_name),
            description=val(draft.description),
            product_type=val(draft.product_type),
            brand=val(draft.brand),
            hsn_code=val(draft.hsn_code),
            gst_percentage=val(draft.gst_percentage),
            fabric_type=val(draft.fabric_type),
            care_instructions=val(draft.care_instructions),
            set_composition=val(draft.set_composition),
            product_media_urls=val(draft.product_media_urls) or [],
            size_chart_url=val(draft.size_chart_url),
            video_urls=val(draft.video_urls) or [],
            collection_tags=val(draft.collection_tags) or []
        )
        
        sku_in = SaveSkuInput(
            sku_internal_id=sku_internal_id,
            sku_id=s_id,
            colour=val(draft.colour),
            size=val(draft.size),
            size_type=val(draft.size_type),
            pack_configuration=val(draft.pack_configuration),
            mrp=val(draft.mrp),
            selling_price=val(draft.selling_price),
            cost_price=val(draft.cost_price),
            packaging_length_cm=val(draft.packaging_length_cm),
            packaging_breadth_cm=val(draft.packaging_breadth_cm),
            packaging_height_cm=val(draft.packaging_height_cm),
            packaging_weight_kg=val(draft.packaging_weight_kg),
            sku_media_urls=val(draft.sku_media_urls) or []
        )

        return SaveProductFamilyPayload(
            product=prod_in,
            skus=[sku_in]
        )
