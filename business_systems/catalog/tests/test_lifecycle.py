"""
Lifecycle State Transition and Mutation Tests for Catalog BS
Validates DRAFT -> READY -> PUBLISHED, post-publication mutation semantics,
aggregate-wide readiness gates, and cross-product parent membership safety.
"""

import pytest
from decimal import Decimal
from catalog.config import CATALOG_DATABASE_URL
from catalog.models import (
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
    RenameProductCodePayload,
    TransitionLifecycleStatePayload,
)
from catalog.service import CatalogService

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def catalog_service():
    service = await CatalogService.create(CATALOG_DATABASE_URL)
    yield service
    await service.close()

async def test_full_lifecycle_flow(catalog_service):
    # 1. Create Product Family in DRAFT
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-LC-TEST01",
            name="Lifecycle Test Product",
            description="<p>Lifecycle Test Product Description</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            gst_percentage=Decimal("5.00"),
            hsn_code="6304",
        ),
        skus=[
            SaveSkuInput(
                sku_id="LC-SKU-01",
                colour="Navy",
                size="Queen",
                mrp=Decimal("2499.00"),
                selling_price=Decimal("1299.00"),
                cost_price=Decimal("550.00"),
                packaging_length_cm=Decimal("35.00"),
                packaging_breadth_cm=Decimal("25.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("1.100"),
                sku_media_urls=["https://media.aaramhomes.com/navy_swatch.jpg"],
            )
        ],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "SUCCESS"
    assert res.lifecycle_state == "DRAFT"
    prod_id = res.product_internal_id

    # 2. Transition from DRAFT to READY
    t_res = await catalog_service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )
    assert t_res.status == "SUCCESS"
    assert t_res.lifecycle_state == "READY"

    # 3. Simulate Publication (Setting state to PUBLISHED in DB)
    async with catalog_service.pool.acquire() as conn:
        await conn.execute(
            "UPDATE catalog_products SET lifecycle_state = 'PUBLISHED' WHERE internal_id = $1;",
            prod_id,
        )

    # 4. Mutate PUBLISHED Product with valid data -> should transition to READY
    payload_edit = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_internal_id=prod_id,
            product_code="AH-LC-TEST01",
            name="Lifecycle Test Product Updated Title",
            brand="Aaram Homes",
        ),
        skus=[
            SaveSkuInput(
                sku_id="LC-SKU-01",
                colour="Navy Blue",
                size="Queen",
                mrp=Decimal("2499.00"),
                selling_price=Decimal("1399.00"),  # Price changed
                cost_price=Decimal("550.00"),
                packaging_length_cm=Decimal("35.00"),
                packaging_breadth_cm=Decimal("25.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("1.100"),
            )
        ],
    )
    edit_res = await catalog_service.save_product_family(payload_edit)
    assert edit_res.status == "SUCCESS"
    assert edit_res.lifecycle_state == "READY"  # Transitioned from PUBLISHED to READY!

    # 5. Rename Product Code
    ren_res = await catalog_service.rename_product_code(
        RenameProductCodePayload(
            product_internal_id=prod_id,
            new_product_code="AH-LC-RENAMED",
        )
    )
    assert ren_res.status == "SUCCESS"
    assert ren_res.product_code == "AH-LC-RENAMED"

    # Verify SKU resolution
    sku_row = await catalog_service.resolve_sku("LC-SKU-01")
    assert sku_row is not None
    assert sku_row["product_code"] == "AH-LC-RENAMED"
    assert sku_row["selling_price"] == Decimal("1399.00")

async def test_cross_product_sku_mutation_rejected(catalog_service):
    """
    Validates Part 5: SKU Identity & Parent Membership Safety.
    Attempting to mutate Product A using a SKU belonging to Product B must be rejected.
    """
    # 1. Create Product A with SKU A
    res_a = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(product_code="AH-PROD-A", name="Product A Family"),
            skus=[
                SaveSkuInput(
                    sku_id="SKU-PROD-A",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_a.status == "SUCCESS"
    prod_a_id = res_a.product_internal_id
    sku_a_id = res_a.sku_internal_ids[0]

    # 2. Create Product B with SKU B
    res_b = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(product_code="AH-PROD-B", name="Product B Family"),
            skus=[
                SaveSkuInput(
                    sku_id="SKU-PROD-B",
                    mrp=Decimal("3000.00"),
                    selling_price=Decimal("1500.00"),
                    cost_price=Decimal("700.00"),
                    packaging_length_cm=Decimal("25.00"),
                    packaging_breadth_cm=Decimal("20.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.800"),
                )
            ],
        )
    )
    assert res_b.status == "SUCCESS"
    prod_b_id = res_b.product_internal_id
    sku_b_id = res_b.sku_internal_ids[0]

    # 3. Attempt to mutate Product A using SKU B's internal_id
    hijack_payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_internal_id=prod_a_id,
            product_code="AH-PROD-A",
            name="Product A Family Mutated",
        ),
        skus=[
            SaveSkuInput(
                sku_internal_id=sku_b_id,  # Points to Product B!
                sku_id="SKU-PROD-B",
                mrp=Decimal("9999.00"),
                selling_price=Decimal("8888.00"),
                cost_price=Decimal("4000.00"),
                packaging_length_cm=Decimal("25.00"),
                packaging_breadth_cm=Decimal("20.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.800"),
            )
        ],
    )
    hijack_res = await catalog_service.save_product_family(hijack_payload)
    assert hijack_res.status == "REJECTED"
    assert any(e.error_code == "CROSS_PRODUCT_SKU_MUTATION_DENIED" for e in hijack_res.errors)

    # 4. Verify SKU B in database was NOT modified
    async with catalog_service.pool.acquire() as conn:
        sku_b_row = await conn.fetchrow("SELECT * FROM catalog_skus WHERE internal_id = $1;", sku_b_id)
        assert sku_b_row["product_internal_id"] == prod_b_id
        assert sku_b_row["mrp"] == Decimal("3000.00")
        assert sku_b_row["selling_price"] == Decimal("1500.00")

async def test_aggregate_readiness_with_invalid_persisted_sibling(catalog_service):
    """
    Validates Phase 3: Aggregate Readiness Invariant.
    If a Product family has an invalid/incomplete persisted sibling SKU, mutating a valid sibling SKU
    must NOT transition the Product to READY.
    """
    # 1. Create Product Family in DRAFT with SKU 1 (Complete) and SKU 2 (Missing media/incomplete)
    res = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-AGG-TEST",
                name="Aggregate Test Family",
                description="<p>Aggregate Test Description</p>",
                product_type="home__bed_linen",
                brand="Aaram Homes",
                gst_percentage=Decimal("5.00"),
                hsn_code="6304",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="AGG-SKU-01",
                    colour="Blue",
                    size="King",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                    sku_media_urls=["https://media.aaramhomes.com/blue.jpg"],
                ),
                SaveSkuInput(
                    sku_id="AGG-SKU-02",
                    colour="Red",
                    size="King",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                    sku_media_urls=[],  # Incomplete! Missing media
                ),
            ],
        )
    )
    assert res.status == "SUCCESS"
    assert res.lifecycle_state == "DRAFT"
    prod_id = res.product_internal_id
    sku_1_id = res.sku_internal_ids[0]
    sku_2_id = res.sku_internal_ids[1]

    # 2. Transition to READY directly should fail due to SKU 2 missing media
    t_res = await catalog_service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )
    assert t_res.status == "REJECTED"

    # 3. Mutate only SKU 1 (valid) - product MUST remain in DRAFT because sibling SKU 2 in DB is incomplete!
    res_mut1 = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_internal_id=prod_id,
                product_code="AH-AGG-TEST",
                name="Aggregate Test Family",
            ),
            skus=[
                SaveSkuInput(
                    sku_internal_id=sku_1_id,
                    sku_id="AGG-SKU-01",
                    mrp=Decimal("2200.00"),
                    selling_price=Decimal("1100.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                    sku_media_urls=["https://media.aaramhomes.com/blue.jpg"],
                )
            ],
        )
    )
    assert res_mut1.status == "SUCCESS"
    assert res_mut1.lifecycle_state == "DRAFT"

    # 4. Now update SKU 2 with complete media
    res_mut2 = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_internal_id=prod_id,
                product_code="AH-AGG-TEST",
                name="Aggregate Test Family",
            ),
            skus=[
                SaveSkuInput(
                    sku_internal_id=sku_2_id,
                    sku_id="AGG-SKU-02",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                    sku_media_urls=["https://media.aaramhomes.com/red.jpg"],
                )
            ],
        )
    )
    assert res_mut2.status == "SUCCESS"

    # 5. Now transition to READY should succeed!
    t_res2 = await catalog_service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )
    assert t_res2.status == "SUCCESS"
    assert t_res2.lifecycle_state == "READY"
