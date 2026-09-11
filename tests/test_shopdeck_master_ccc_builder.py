"""
Direct coverage for ShopDeckMasterCCCBuilder - the class actually wired live in
src/main.py (`ccc_builder = ShopDeckMasterCCCBuilder(...)`). Before this file existed, no
test in the repo ever instantiated this class: test_ndr_full_context_wiring.py exclusively
exercises the legacy CustomerConversationContextBuilder.

The fixture below is not invented - it mirrors the exact real shape captured on 2026-09-12
by directly calling ShopdeckCemAdapter.execute_evidence_request() against a real local
ShopDeck instance (AWB 371070757553) and dumping the raw response. An earlier version of
this fixture (and the code it tested against) assumed catalog_context didn't exist at all,
based only on confirming Brain's own code never constructs that key - which says nothing
about what ShopDeck's real API actually returns. That assumption was wrong: catalog_context
is real, and the enrichment fields are nested inside it exactly as this fixture shows
(size under variant_shipped.attributes, mrp/selling_price under
variant_shipped.financials as mrp_inr/selling_price_inr, not flat fields on product).
"""
from unittest.mock import AsyncMock

import pytest

from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ConversationalDirective
from src.brain_core.context_engine.ccc_builder import ShopDeckMasterCCCBuilder
from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus


SHOPDECK_EVIDENCE_WITH_CATALOG_DATA = {
    "customer_name": "Rahul",
    "customer.attribute.phone": "9999999999",
    "cod_amount": 499.0,
    "payment_mode": "cod",
    "ndr_count": 1,
    "items": [{"sku_id": "SKU1", "product_name": "Cotton Bedsheet", "quantity": 1, "selling_price": 499.0}],
    # Real shape, verified live against ShopDeck's own API (see module docstring) - nested
    # under catalog_context, not at the evidence root.
    "catalog_context": {
        "product": {
            "name": "Midnight Blue Stripes 300 TC Pure Cotton Bedsheet Set",
            "description": "300 thread count cotton bedsheet set",
            "attributes": {"color": "Teal Blue", "brand_seller": "Aaram Homes"},
            "taxonomy": {"category": None, "sub_category": None, "product_type": None},
            "category_intelligence": {"product_category": "bedsheet", "classification_confidence": "HIGH"},
        },
        "variant_shipped": {
            "attributes": {"size": "108 x 108 inches"},
            "financials": {"mrp_inr": 799.0, "selling_price_inr": 499.0, "gst_percentage": 5.0},
            "policies": {"return_policy_description": "Return/Exchange within three days, wrong or damaged items only"},
            "identifiers": {"system_sku_id": "SKU1", "seller_sku_code": "111BS"},
        },
    },
    # category_intelligence also appears at the evidence root in real responses (identical
    # to the nested copy under catalog_context.product) - the code reads the root copy.
    "category_intelligence": {"product_category": "bedsheet", "classification_confidence": 0.94},
}


def _mock_provider(evidence: dict) -> AsyncMock:
    provider = AsyncMock()
    provider.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data=evidence,
    )
    return provider


def _action_request() -> ActionRequest:
    directive = ConversationalDirective(objective="x", context_summary="y", allowed_actions=[], constraints=[])
    return ActionRequest(
        action_request_id="a1",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="test",
        parameters={"awb_no": "AWB123"},
        directive=directive,
    )


@pytest.mark.asyncio
async def test_build_does_not_crash_on_a_realistic_response_with_items():
    """
    Regression test for the catalog_ctx NameError originally found here, and separately
    for the "catalog_context doesn't exist" mistake that replaced it - both previously made
    this class fail on every real order with items.
    """
    builder = ShopDeckMasterCCCBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE_WITH_CATALOG_DATA))
    ccc = await builder.build(_action_request())
    assert ccc.product_context.rich_attributes_available is True


@pytest.mark.asyncio
async def test_numeric_classification_confidence_does_not_crash_pydantic_validation():
    """
    Regression test for the category_confidence type mismatch: classification_confidence
    is a float in this fixture's root-level category_intelligence (as confirmed live - some
    real responses use a float, others a categorical string like "LOW"), and
    ProductContext/NDRConversationProjection type category_confidence as Optional[str].
    """
    builder = ShopDeckMasterCCCBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE_WITH_CATALOG_DATA))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.category_confidence == "0.94"


@pytest.mark.asyncio
async def test_catalog_enrichment_fields_are_extracted_from_the_real_nested_shape():
    """
    Verifies extraction from the real, live-confirmed nested paths: size from
    variant_shipped.attributes, color from product.attributes, mrp/selling_price from
    variant_shipped.financials (as mrp_inr/selling_price_inr, not flat fields).
    """
    builder = ShopDeckMasterCCCBuilder(provider=_mock_provider(SHOPDECK_EVIDENCE_WITH_CATALOG_DATA))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.catalog_selling_price == 499.0
    assert projection.mrp == 799.0
    assert projection.size == "108 x 108 inches"
    assert projection.color == "Teal Blue"
    assert projection.return_exchange_condition == "Return/Exchange within three days, wrong or damaged items only"
    assert projection.product_category == "bedsheet"


@pytest.mark.asyncio
async def test_missing_catalog_enrichment_data_is_absent_not_crashing():
    """
    When ShopDeck's response has items but no catalog_context key at all (e.g. a genuinely
    uncatalogued SKU), the builder must degrade to absent fields, not crash and not invent
    placeholder values.
    """
    evidence = dict(SHOPDECK_EVIDENCE_WITH_CATALOG_DATA)
    del evidence["catalog_context"]
    del evidence["category_intelligence"]
    builder = ShopDeckMasterCCCBuilder(provider=_mock_provider(evidence))
    ccc = await builder.build(_action_request())
    assert ccc.product_context.rich_attributes_available is False
    assert ccc.product_context.catalog_selling_price is None
    assert ccc.product_context.mrp is None
    assert ccc.product_context.category_confidence is None


@pytest.mark.asyncio
async def test_customer_full_address_reaches_the_projection():
    evidence = dict(SHOPDECK_EVIDENCE_WITH_CATALOG_DATA)
    evidence["customer_full_address"] = "123 MG Road, Bengaluru, 560001"
    builder = ShopDeckMasterCCCBuilder(provider=_mock_provider(evidence))
    ccc = await builder.build(_action_request())
    projection = builder.project(ccc)
    assert projection.customer_full_address == "123 MG Road, Bengaluru, 560001"
