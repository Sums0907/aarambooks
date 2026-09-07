"""
Unit & Integration Tests for Catalog BS Public Read Contracts
Validates exact column projection, derived fields, view joins, and information_schema data types against documents 04 and 06.
"""

import pytest
from decimal import Decimal
from catalog.config import CATALOG_DATABASE_URL
from catalog.models import SaveProductFamilyPayload, SaveProductInput, SaveSkuInput
from catalog.service import CatalogService

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def catalog_service():
    service = await CatalogService.create(CATALOG_DATABASE_URL)
    yield service
    await service.close()

async def test_view_projections_and_derived_margin(catalog_service):
    # 1. Insert product and SKU via service
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-VIEW-TEST",
            name="View Contract Test Bedsheet",
            description="High thread count cotton bedsheet",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            hsn_code="6302",
            gst_percentage=Decimal("12.00"),
            fabric_type="100% Glace Cotton",
            care_instructions="Gentle Machine Wash",
            set_composition="1 Fitted Sheet + 2 Pillow Covers",
            product_media_urls=["https://media.aaramhomes.com/lifestyle_view.jpg"],
            size_chart_url="https://media.aaramhomes.com/size_chart.png",
            video_urls=["https://media.aaramhomes.com/video1.mp4"],
            collection_tags=["cotton-bedsheets", "fitted"],
        ),
        skus=[
            SaveSkuInput(
                sku_id="VIEW-SKU1",
                colour="Emerald Green",
                size="Super King",
                size_type="size",
                pack_configuration="Pack of 1",
                mrp=Decimal("3499.00"),
                selling_price=Decimal("1999.00"),
                cost_price=Decimal("850.00"),
                packaging_length_cm=Decimal("40.00"),
                packaging_breadth_cm=Decimal("30.00"),
                packaging_height_cm=Decimal("7.00"),
                packaging_weight_kg=Decimal("1.450"),
                sku_media_urls=["https://media.aaramhomes.com/green_swatch.jpg"],
            )
        ],
    )
    res = await catalog_service.save_product_family(payload)
    assert res.status == "SUCCESS"
    prod_id = res.product_internal_id
    sku_id = res.sku_internal_ids[0]

    # Map SKU to external ShopDeck channel token
    async with catalog_service.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO catalog_channel_mappings (
                channel, sku_internal_id, external_sku_token, external_product_token
            ) VALUES ('SHOPDECK', $1, 'SD-EXT-SKU-99', 'SD-EXT-PRD-99');
            """,
            sku_id,
        )

        # 2. Test vw_catalog_products
        prod_row = await conn.fetchrow(
            "SELECT * FROM vw_catalog_products WHERE product_internal_id = $1;", prod_id
        )
        assert prod_row is not None
        assert prod_row["product_code"] == "AH-VIEW-TEST"
        assert prod_row["product_name"] == "View Contract Test Bedsheet"
        assert prod_row["brand"] == "Aaram Homes"
        assert prod_row["hsn_code"] == "6302"
        assert prod_row["gst_percentage"] == Decimal("12.00")
        assert prod_row["fabric_type"] == "100% Glace Cotton"
        assert prod_row["care_instructions"] == "Gentle Machine Wash"
        assert prod_row["set_composition"] == "1 Fitted Sheet + 2 Pillow Covers"
        assert prod_row["size_chart_url"] == "https://media.aaramhomes.com/size_chart.png"
        assert prod_row["lifecycle_state"] == "DRAFT"

        # 3. Test vw_catalog_skus
        sku_row = await conn.fetchrow(
            "SELECT * FROM vw_catalog_skus WHERE sku_internal_id = $1;", sku_id
        )
        assert sku_row is not None
        assert sku_row["sku_id"] == "VIEW-SKU1"
        assert sku_row["colour"] == "Emerald Green"
        assert sku_row["size"] == "Super King"
        assert sku_row["mrp"] == Decimal("3499.00")
        assert sku_row["selling_price"] == Decimal("1999.00")
        assert sku_row["cost_price"] == Decimal("850.00")
        assert sku_row["gross_margin"] == Decimal("1149.00")  # 1999.00 - 850.00
        assert sku_row["packaging_length_cm"] == Decimal("40.00")
        assert sku_row["packaging_weight_kg"] == Decimal("1.450")

        # 4. Test vw_catalog_master
        master_row = await conn.fetchrow(
            "SELECT * FROM vw_catalog_master WHERE sku_internal_id = $1;", sku_id
        )
        assert master_row is not None
        assert master_row["product_code"] == "AH-VIEW-TEST"
        assert master_row["sku_id"] == "VIEW-SKU1"
        assert master_row["gross_margin"] == Decimal("1149.00")
        assert master_row["shopdeck_sku_id"] == "SD-EXT-SKU-99"
        assert master_row["shopdeck_product_id"] == "SD-EXT-PRD-99"

        # 5. Verify absence of prohibited lifecycle fields in all views
        for row in [prod_row, sku_row, master_row]:
            keys = list(row.keys())
            assert "is_active" not in keys
            assert "retired" not in keys
            assert "is_deleted" not in keys

async def test_database_views_information_schema_contract(catalog_service):
    """
    Field-by-field verification of public views against 04-catalog-contracts.md Section 6.
    Inspects PostgreSQL information_schema to verify exact column names and physical data types.
    """
    async with catalog_service.pool.acquire() as conn:
        # 1. Inspect vw_catalog_products (18 columns)
        prod_cols = await conn.fetch(
            """
            SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'vw_catalog_products'
            ORDER BY ordinal_position;
            """
        )
        prod_col_map = {r["column_name"]: r for r in prod_cols}
        assert len(prod_cols) == 18

        assert prod_col_map["product_internal_id"]["data_type"] == "uuid"
        assert prod_col_map["product_code"]["data_type"] == "character varying"
        assert prod_col_map["product_code"]["character_maximum_length"] == 24
        assert prod_col_map["product_name"]["data_type"] == "text"
        assert prod_col_map["description"]["data_type"] == "text"
        assert prod_col_map["product_type"]["data_type"] == "character varying"
        assert prod_col_map["product_type"]["character_maximum_length"] == 128
        assert prod_col_map["brand"]["data_type"] == "character varying"
        assert prod_col_map["brand"]["character_maximum_length"] == 64
        assert prod_col_map["hsn_code"]["data_type"] == "character varying"
        assert prod_col_map["hsn_code"]["character_maximum_length"] == 10
        assert prod_col_map["gst_percentage"]["data_type"] == "numeric"
        assert prod_col_map["gst_percentage"]["numeric_precision"] == 4
        assert prod_col_map["gst_percentage"]["numeric_scale"] == 2
        assert prod_col_map["fabric_type"]["data_type"] == "text"
        assert prod_col_map["care_instructions"]["data_type"] == "text"
        assert prod_col_map["set_composition"]["data_type"] == "text"
        assert prod_col_map["product_media_urls"]["data_type"] == "jsonb"
        assert prod_col_map["size_chart_url"]["data_type"] == "text"
        assert prod_col_map["video_urls"]["data_type"] == "jsonb"
        assert prod_col_map["collection_tags"]["data_type"] == "ARRAY"
        assert prod_col_map["lifecycle_state"]["data_type"] == "character varying"
        assert prod_col_map["lifecycle_state"]["character_maximum_length"] == 32
        assert prod_col_map["created_at"]["data_type"] == "timestamp with time zone"
        assert prod_col_map["updated_at"]["data_type"] == "timestamp with time zone"

        # 2. Inspect vw_catalog_skus (20 columns)
        sku_cols = await conn.fetch(
            """
            SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'vw_catalog_skus'
            ORDER BY ordinal_position;
            """
        )
        sku_col_map = {r["column_name"]: r for r in sku_cols}
        assert len(sku_cols) == 20

        assert sku_col_map["sku_internal_id"]["data_type"] == "uuid"
        assert sku_col_map["product_internal_id"]["data_type"] == "uuid"
        assert sku_col_map["product_code"]["data_type"] == "character varying"
        assert sku_col_map["sku_id"]["data_type"] == "character varying"
        assert sku_col_map["sku_id"]["character_maximum_length"] == 10
        assert sku_col_map["colour"]["data_type"] == "character varying"
        assert sku_col_map["size"]["data_type"] == "character varying"
        assert sku_col_map["size_type"]["data_type"] == "character varying"
        assert sku_col_map["pack_configuration"]["data_type"] == "character varying"
        assert sku_col_map["mrp"]["data_type"] == "numeric"
        assert sku_col_map["mrp"]["numeric_precision"] == 10
        assert sku_col_map["mrp"]["numeric_scale"] == 2
        assert sku_col_map["selling_price"]["data_type"] == "numeric"
        assert sku_col_map["selling_price"]["numeric_precision"] == 10
        assert sku_col_map["selling_price"]["numeric_scale"] == 2
        assert sku_col_map["cost_price"]["data_type"] == "numeric"
        assert sku_col_map["cost_price"]["numeric_precision"] == 10
        assert sku_col_map["cost_price"]["numeric_scale"] == 2
        assert sku_col_map["gross_margin"]["data_type"] == "numeric"
        assert sku_col_map["packaging_length_cm"]["data_type"] == "numeric"
        assert sku_col_map["packaging_length_cm"]["numeric_precision"] == 6
        assert sku_col_map["packaging_length_cm"]["numeric_scale"] == 2
        assert sku_col_map["packaging_weight_kg"]["data_type"] == "numeric"
        assert sku_col_map["packaging_weight_kg"]["numeric_precision"] == 6
        assert sku_col_map["packaging_weight_kg"]["numeric_scale"] == 3
        assert sku_col_map["sku_media_urls"]["data_type"] == "jsonb"

        # 3. Inspect vw_catalog_master (35 columns)
        master_cols = await conn.fetch(
            """
            SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'vw_catalog_master'
            ORDER BY ordinal_position;
            """
        )
        master_col_map = {r["column_name"]: r for r in master_cols}
        assert len(master_cols) == 35

        assert master_col_map["sku_internal_id"]["data_type"] == "uuid"
        assert master_col_map["product_internal_id"]["data_type"] == "uuid"
        assert master_col_map["sku_id"]["data_type"] == "character varying"
        assert master_col_map["product_code"]["data_type"] == "character varying"
        assert master_col_map["product_name"]["data_type"] == "text"
        assert master_col_map["product_type"]["data_type"] == "character varying"
        assert master_col_map["product_type"]["character_maximum_length"] == 128
        assert master_col_map["gst_percentage"]["data_type"] == "numeric"
        assert master_col_map["gst_percentage"]["numeric_precision"] == 4
        assert master_col_map["gst_percentage"]["numeric_scale"] == 2
        assert master_col_map["fabric_type"]["data_type"] == "text"
        assert master_col_map["set_composition"]["data_type"] == "text"
        assert master_col_map["gross_margin"]["data_type"] == "numeric"
        assert master_col_map["shopdeck_sku_id"]["data_type"] == "character varying"
        assert master_col_map["shopdeck_product_id"]["data_type"] == "character varying"
