"""
Complete End-to-End System Certification Test for Catalog BS
Exercises the full lifecycle, mutations, price ledgering, ShopDeck publication, and public read views.
"""

import csv
import io
import os
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
from catalog.shopdeck_adapter import ShopDeckAdapter, SHOPDECK_46_COLUMNS

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def system_services():
    service = await CatalogService.create(CATALOG_DATABASE_URL)
    adapter = await ShopDeckAdapter.create(CATALOG_DATABASE_URL)
    yield service, adapter
    await adapter.close()
    await service.close()

async def test_full_catalog_bs_end_to_end(system_services, tmp_path):
    service, adapter = system_services

    # =========================================================================
    # STEP 1: CREATE PRODUCT FAMILY IN DRAFT STATE
    # =========================================================================
    payload_1 = SaveProductFamilyPayload(
        idempotency_key="e2e-step-1-create",
        product=SaveProductInput(
            product_code="AH-E2E-01",
            name="End-to-End Luxury Duvet Cover",
            description="<p>100% Egyptian Cotton luxury duvet cover set.</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            hsn_code="6302",
            gst_percentage=Decimal("5.00"),
            fabric_type="100% Egyptian Cotton",
            care_instructions="Machine Wash Warm",
            set_composition="1 Duvet Cover + 2 Pillow Shams",
            product_media_urls=[
                "https://media.aaramhomes.com/duvet_main.jpg",
                "https://media.aaramhomes.com/duvet_lifestyle.jpg",
            ],
            collection_tags=["duvet-covers", "luxury-bedding"],
        ),
        skus=[
            SaveSkuInput(
                sku_id="E2E-SKU-01",
                colour="Ivory White",
                size="King",
                size_type="size",
                pack_configuration="Pack of 1",
                mrp=Decimal("4999.00"),
                selling_price=Decimal("2999.00"),
                cost_price=Decimal("1200.00"),
                packaging_length_cm=Decimal("42.00"),
                packaging_breadth_cm=Decimal("32.00"),
                packaging_height_cm=Decimal("8.00"),
                packaging_weight_kg=Decimal("1.800"),
                sku_media_urls=["https://media.aaramhomes.com/ivory_swatch.jpg"],
            ),
            SaveSkuInput(
                sku_id="E2E-SKU-02",
                colour="Charcoal Grey",
                size="King",
                size_type="size",
                pack_configuration="Pack of 1",
                mrp=Decimal("4999.00"),
                selling_price=Decimal("2999.00"),
                cost_price=Decimal("1200.00"),
                packaging_length_cm=Decimal("42.00"),
                packaging_breadth_cm=Decimal("32.00"),
                packaging_height_cm=Decimal("8.00"),
                packaging_weight_kg=Decimal("1.800"),
                sku_media_urls=["https://media.aaramhomes.com/charcoal_swatch.jpg"],
            ),
        ],
    )
    res_1 = await service.save_product_family(payload_1)
    assert res_1.status == "SUCCESS"
    assert res_1.lifecycle_state == "DRAFT"
    assert res_1.affected_sku_count == 2
    prod_id = res_1.product_internal_id
    sku_1_id = res_1.sku_internal_ids[0]

    # Verify initial price history entries created for both SKUs
    async with service.pool.acquire() as conn:
        ph_count = await conn.fetchval(
            "SELECT count(*) FROM catalog_price_history WHERE sku_internal_id = $1;", sku_1_id
        )
        assert ph_count == 1

    # =========================================================================
    # STEP 2: PRICE UPDATE & AUDIT LEDGERING
    # =========================================================================
    payload_2 = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_internal_id=prod_id,
            product_code="AH-E2E-01",
            name="End-to-End Luxury Duvet Cover",
            brand="Aaram Homes",
        ),
        skus=[
            SaveSkuInput(
                sku_internal_id=sku_1_id,
                sku_id="E2E-SKU-01",
                colour="Ivory White",
                size="King",
                mrp=Decimal("4999.00"),
                selling_price=Decimal("2799.00"),  # Festive price discount
                cost_price=Decimal("1200.00"),
                packaging_length_cm=Decimal("42.00"),
                packaging_breadth_cm=Decimal("32.00"),
                packaging_height_cm=Decimal("8.00"),
                packaging_weight_kg=Decimal("1.800"),
            )
        ],
    )
    res_2 = await service.save_product_family(payload_2)
    assert res_2.status == "SUCCESS"

    # Verify second price history record logged with previous prices matching 06-catalog-data-schema.md
    async with service.pool.acquire() as conn:
        ph_records = await conn.fetch(
            "SELECT * FROM catalog_price_history WHERE sku_internal_id = $1 ORDER BY id DESC;", sku_1_id
        )
        assert len(ph_records) == 2
        assert ph_records[0]["previous_selling_price"] == Decimal("2999.00")
        assert ph_records[0]["new_selling_price"] == Decimal("2799.00")

    # =========================================================================
    # STEP 3: TRANSITION TO READY STATE
    # =========================================================================
    res_3 = await service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )
    assert res_3.status == "SUCCESS"
    assert res_3.lifecycle_state == "READY"

    # =========================================================================
    # STEP 4: SHOPDECK 46-COLUMN CSV COMPILATION & PUBLICATION
    # =========================================================================
    artifact, csv_content = await adapter.generate_publication_artifact(
        target_product_internal_ids=[prod_id],
        output_dir=str(tmp_path),
        generated_by="E2E_CERTIFIER",
    )
    assert artifact.channel == "SHOPDECK"
    assert artifact.exported_sku_count >= 1
    assert os.path.exists(artifact.file_path)

    # Verify CSV format and headers
    reader = csv.DictReader(io.StringIO(csv_content))
    assert reader.fieldnames == SHOPDECK_46_COLUMNS
    assert len(reader.fieldnames) == 46

    # Verify product transitioned to PUBLISHED
    async with service.pool.acquire() as conn:
        state = await conn.fetchval(
            "SELECT lifecycle_state FROM catalog_products WHERE internal_id = $1;", prod_id
        )
        assert state == "PUBLISHED"

    # =========================================================================
    # STEP 5: MUTATION OF PUBLISHED PRODUCT -> TRANSITIONS TO READY
    # =========================================================================
    payload_edit_published = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_internal_id=prod_id,
            product_code="AH-E2E-01",
            name="End-to-End Luxury Duvet Cover - Edition 2",
            brand="Aaram Homes",
        ),
        skus=[
            SaveSkuInput(
                sku_internal_id=sku_1_id,
                sku_id="E2E-SKU-01",
                mrp=Decimal("4999.00"),
                selling_price=Decimal("2799.00"),
                cost_price=Decimal("1200.00"),
                packaging_length_cm=Decimal("42.00"),
                packaging_breadth_cm=Decimal("32.00"),
                packaging_height_cm=Decimal("8.00"),
                packaging_weight_kg=Decimal("1.800"),
            )
        ],
    )
    res_edit = await service.save_product_family(payload_edit_published)
    assert res_edit.status == "SUCCESS"
    assert res_edit.lifecycle_state == "READY"  # Successfully reset to READY!

    # =========================================================================
    # STEP 6: RENAME PRODUCT CODE & VIEW RESOLUTION
    # =========================================================================
    res_ren = await service.rename_product_code(
        RenameProductCodePayload(
            product_internal_id=prod_id,
            new_product_code="AH-E2E-RENAMED",
        )
    )
    assert res_ren.status == "SUCCESS"
    assert res_ren.product_code == "AH-E2E-RENAMED"

    # Verify resolution via resolve_sku
    resolved = await service.resolve_sku("E2E-SKU-01")
    assert resolved is not None
    assert resolved["product_code"] == "AH-E2E-RENAMED"
    assert resolved["product_name"] == "End-to-End Luxury Duvet Cover - Edition 2"
    assert resolved["gross_margin"] == Decimal("1599.00")  # 2799.00 - 1200.00
