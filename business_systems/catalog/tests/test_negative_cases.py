"""
Negative & Error Condition Tests for Catalog BS
Validates that invalid inputs, invariants violations, and unsafe operations are reliably rejected.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from catalog.config import CATALOG_DATABASE_URL
from catalog.models import (
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
    TransitionLifecycleStatePayload,
)
from catalog.service import CatalogService
from catalog.shopdeck_adapter import ShopDeckAdapter

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def catalog_service():
    service = await CatalogService.create(CATALOG_DATABASE_URL)
    yield service
    await service.close()

async def test_negative_invalid_product_code_rejected(catalog_service):
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="bad_code",  # Lowercase + underscore
            name="Bad Code Product",
        ),
        skus=[],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "REJECTED"
    assert any(e.error_code == "SYNTAX_VALIDATION_ERROR" for e in res.errors)

async def test_negative_price_ceiling_violation_rejected(catalog_service):
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-NEG-PRICE",
            name="Negative Price Test Product",
        ),
        skus=[
            SaveSkuInput(
                sku_id="NEG-PRC-01",
                mrp=Decimal("1000.00"),
                selling_price=Decimal("1500.00"),  # Violates selling_price <= mrp
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
            )
        ],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "REJECTED"
    assert any(e.error_code == "PRICING_INVARIANT_VIOLATION" for e in res.errors)

async def test_negative_dimension_out_of_bounds_rejected(catalog_service):
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-NEG-DIM",
            name="Negative Dimension Product",
        ),
        skus=[
            SaveSkuInput(
                sku_id="NEG-DIM-01",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("75.00"),  # > 50 cm max
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
            )
        ],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "REJECTED"
    assert any(e.error_code == "PHYSICAL_SPEC_VIOLATION" for e in res.errors)

async def test_negative_weight_out_of_bounds_rejected(catalog_service):
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-NEG-WT",
            name="Negative Weight Product",
        ),
        skus=[
            SaveSkuInput(
                sku_id="NEG-WT-01",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("25.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.010"),  # < 0.050 kg min
            )
        ],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "REJECTED"
    assert any(e.error_code == "PHYSICAL_SPEC_VIOLATION" for e in res.errors)

async def test_negative_invalid_lifecycle_transition_target(catalog_service):
    # Direct manual transition to PUBLISHED must be rejected
    res = await catalog_service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=uuid4(),
            target_state="PUBLISHED",  # Prohibited direct manual transition
        )
    )
    assert res.status == "REJECTED"
    assert any(e.error_code == "INVALID_LIFECYCLE_TRANSITION" for e in res.errors)

async def test_negative_transition_ready_with_no_skus_rejected(catalog_service):
    # Create product with 0 SKUs
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-NEG-NOSKU",
            name="Empty Product",
        ),
        skus=[],
    )
    save_res = await catalog_service.save_product_family(payload)
    assert save_res.status == "SUCCESS"
    prod_id = save_res.product_internal_id

    # Attempt transition to READY
    t_res = await catalog_service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )
    assert t_res.status == "REJECTED"
    assert any(e.error_code in ("READINESS_GATE_FAILED", "LIFECYCLE_COMPLETENESS_ERROR") for e in t_res.errors)

async def test_negative_shopdeck_preflight_equal_prices_rejected():
    adapter = ShopDeckAdapter(None)
    row = {
        "sku_id": "SD-TEST-01",
        "mrp": Decimal("1000.00"),
        "selling_price": Decimal("1000.00"),  # Equal to MRP -> violates ShopDeck preflight
    }
    errs = adapter.audit_preflight_row(row)
    assert len(errs) == 1
    assert errs[0].error_code == "SHOPDECK_PRICE_INEQUALITY_VIOLATION"

async def test_negative_product_name_too_short_rejected(catalog_service):
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-SHORT-NAME",
            name="Bed",  # < 5 characters
        ),
        skus=[],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "REJECTED"
    assert any(e.error_code == "SYNTAX_VALIDATION_ERROR" and e.target_field == "name" for e in res.errors)
