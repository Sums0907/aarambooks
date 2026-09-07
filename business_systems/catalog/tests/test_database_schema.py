"""
Database Schema & Constraint Tests for Catalog BS
Validates all PostgreSQL physical tables, check constraints, triggers, and views.
"""

import pytest
import asyncpg
from decimal import Decimal

pytestmark = pytest.mark.asyncio

async def test_product_insert_and_constraints(db_conn):
    # Valid product insert
    p_id = await db_conn.fetchval("""
        INSERT INTO catalog_products (
            product_code, name, description, product_type, brand, hsn_code, gst_percentage, fabric_type, set_composition
        ) VALUES (
            'AH-MP-WATERPROOF', '100% Waterproof Mattress Protector', 'Description text',
            'home__home_furnishing__bed_linen', 'Aaram Homes', '6304', 5.00, 'Cotton Blend', '1 Protector'
        ) RETURNING internal_id;
    """)
    assert p_id is not None

    # Duplicate product_code should fail
    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_products (product_code, name)
                VALUES ('AH-MP-WATERPROOF', 'Duplicate Code');
            """)

    # Invalid product_code format (lowercase) should fail
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_products (product_code, name)
                VALUES ('ah-mp-waterproof', 'Lowercase Code');
            """)

    # Invalid product_code length (< 5) should fail
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_products (product_code, name)
                VALUES ('AH-1', 'Short Code Product');
            """)

    # Invalid product name length (< 5) must fail at database level (chk_product_name_minlen)
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_products (product_code, name)
                VALUES ('AH-SHORT-NAME', 'Bed');
            """)

    # Invalid GST rate (< 0.0) should fail
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_products (product_code, name, gst_percentage)
                VALUES ('AH-GST-INVALID', 'Invalid GST Rate Product', -5.00);
            """)

async def test_sku_insert_and_pricing_constraints(db_conn):
    p_id = await db_conn.fetchval("""
        INSERT INTO catalog_products (product_code, name)
        VALUES ('AH-BS-PASTEL', 'Pastel Bedsheet Collection')
        RETURNING internal_id;
    """)

    # Valid SKU insert
    s_id = await db_conn.fetchval("""
        INSERT INTO catalog_skus (
            product_internal_id, sku_id, colour, size, size_type, pack_configuration,
            mrp, selling_price, cost_price,
            packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
        ) VALUES (
            $1, '126BS-BLU', 'Sky Blue', 'King', 'size', 'Pack of 1',
            2999.00, 1499.00, 650.00,
            38.00, 30.00, 6.00, 1.250
        ) RETURNING internal_id;
    """, p_id)
    assert s_id is not None

    # Duplicate sku_id should fail
    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_skus (
                    product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES (
                    $1, '126BS-BLU', 2999.00, 1499.00, 650.00, 38.00, 30.00, 6.00, 1.250
                );
            """, p_id)

    # Price ceiling violation (selling_price > mrp) should fail
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_skus (
                    product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES (
                    $1, '126BS-RED', 1000.00, 1500.00, 500.00, 38.00, 30.00, 6.00, 1.250
                );
            """, p_id)

    # Invalid dimensions (> 50 cm) should fail
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_skus (
                    product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES (
                    $1, '126BS-GRN', 2000.00, 1000.00, 500.00, 60.00, 30.00, 6.00, 1.250
                );
            """, p_id)

    # Invalid weight (< 0.05 kg) should fail
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_skus (
                    product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES (
                    $1, '126BS-YEL', 2000.00, 1000.00, 500.00, 30.00, 30.00, 6.00, 0.010
                );
            """, p_id)

async def test_price_history_and_referential_integrity(db_conn):
    p_id = await db_conn.fetchval("""
        INSERT INTO catalog_products (product_code, name)
        VALUES ('AH-PH-TEST', 'Price History Test Product')
        RETURNING internal_id;
    """)

    s_id = await db_conn.fetchval("""
        INSERT INTO catalog_skus (
            product_internal_id, sku_id, mrp, selling_price, cost_price,
            packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
        ) VALUES (
            $1, 'PHTEST-01', 2000.00, 1500.00, 600.00, 30.00, 25.00, 5.00, 1.000
        ) RETURNING internal_id;
    """, p_id)

    # Insert price history record with authoritative column names from 06-catalog-data-schema.md
    await db_conn.execute("""
        INSERT INTO catalog_price_history (
            sku_internal_id, previous_mrp, new_mrp, previous_selling_price, new_selling_price,
            previous_cost_price, new_cost_price, changed_by
        ) VALUES ($1, 2000.00, 1800.00, 1500.00, 1299.00, 600.00, 600.00, 'SYSTEM');
    """, s_id)

    # Attempting to delete SKU must fail due to ON DELETE RESTRICT on price history
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        async with db_conn.transaction():
            await db_conn.execute("DELETE FROM catalog_skus WHERE internal_id = $1;", s_id)

    # Attempting direct UPDATE on price history must fail due to immutability trigger
    with pytest.raises(asyncpg.PostgresError):
        async with db_conn.transaction():
            await db_conn.execute("UPDATE catalog_price_history SET new_selling_price = 999.00 WHERE sku_internal_id = $1;", s_id)

    # Attempting direct DELETE on price history must fail due to immutability trigger
    with pytest.raises(asyncpg.PostgresError):
        async with db_conn.transaction():
            await db_conn.execute("DELETE FROM catalog_price_history WHERE sku_internal_id = $1;", s_id)

async def test_channel_mappings_and_uniqueness(db_conn):
    p_id = await db_conn.fetchval("""
        INSERT INTO catalog_products (product_code, name)
        VALUES ('AH-MAP-TEST', 'Mapping Test Product')
        RETURNING internal_id;
    """)

    s_id = await db_conn.fetchval("""
        INSERT INTO catalog_skus (
            product_internal_id, sku_id, mrp, selling_price, cost_price,
            packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
        ) VALUES (
            $1, 'MAPTEST-1', 2000.00, 1500.00, 600.00, 30.00, 25.00, 5.00, 1.000
        ) RETURNING internal_id;
    """, p_id)

    # Insert mapping
    await db_conn.execute("""
        INSERT INTO catalog_channel_mappings (
            channel, sku_internal_id, external_sku_token, external_product_token
        ) VALUES ('SHOPDECK', $1, 'SD-SKU-TOK1', 'SD-PRD-TOK1');
    """, s_id)

    # Duplicate mapping for same (channel, sku_internal_id) must fail
    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_channel_mappings (
                    channel, sku_internal_id, external_sku_token, external_product_token
                ) VALUES ('SHOPDECK', $1, 'SD-SKU-TOK2', 'SD-PRD-TOK1');
            """, s_id)

    # Duplicate mapping for same (channel, external_sku_token) must fail
    s_id_2 = await db_conn.fetchval("""
        INSERT INTO catalog_skus (
            product_internal_id, sku_id, mrp, selling_price, cost_price,
            packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
        ) VALUES (
            $1, 'MAPTEST-2', 2000.00, 1500.00, 600.00, 30.00, 25.00, 5.00, 1.000
        ) RETURNING internal_id;
    """, p_id)

    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute("""
                INSERT INTO catalog_channel_mappings (
                    channel, sku_internal_id, external_sku_token, external_product_token
                ) VALUES ('SHOPDECK', $1, 'SD-SKU-TOK1', 'SD-PRD-TOK1');
            """, s_id_2)

async def test_updated_at_trigger(db_conn):
    p_id = await db_conn.fetchval("""
        INSERT INTO catalog_products (product_code, name)
        VALUES ('AH-TRG-TEST', 'Trigger Test Product')
        RETURNING internal_id;
    """)

    row1 = await db_conn.fetchrow("SELECT created_at, updated_at FROM catalog_products WHERE internal_id = $1;", p_id)
    assert row1['created_at'] == row1['updated_at']

    # Update product
    await db_conn.execute("UPDATE catalog_products SET name = 'Trigger Test Updated Product' WHERE internal_id = $1;", p_id)
    row2 = await db_conn.fetchrow("SELECT created_at, updated_at FROM catalog_products WHERE internal_id = $1;", p_id)
    assert row2['updated_at'] >= row1['updated_at']

async def test_public_views_projections(db_conn):
    p_id = await db_conn.fetchval("""
        INSERT INTO catalog_products (
            product_code, name, description, brand, hsn_code, gst_percentage
        ) VALUES (
            'AH-VIEW-01', 'Unified View Product', 'Description', 'Aaram Homes', '6304', 5.00
        ) RETURNING internal_id;
    """)

    s_id = await db_conn.fetchval("""
        INSERT INTO catalog_skus (
            product_internal_id, sku_id, colour, size, mrp, selling_price, cost_price,
            packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
        ) VALUES (
            $1, 'VIEW-SKU1', 'Maroon', 'Double', 3000.00, 2000.00, 800.00,
            35.00, 25.00, 5.00, 1.100
        ) RETURNING internal_id;
    """, p_id)

    await db_conn.execute("""
        INSERT INTO catalog_channel_mappings (
            channel, sku_internal_id, external_sku_token, external_product_token
        ) VALUES ('SHOPDECK', $1, 'SD-VIEW-SKU', 'SD-VIEW-PRD');
    """, s_id)

    # 1. Query vw_catalog_products
    v_prod = await db_conn.fetchrow("SELECT * FROM vw_catalog_products WHERE product_internal_id = $1;", p_id)
    assert v_prod is not None
    assert v_prod['product_code'] == 'AH-VIEW-01'

    # 2. Query vw_catalog_skus
    v_sku = await db_conn.fetchrow("SELECT * FROM vw_catalog_skus WHERE sku_internal_id = $1;", s_id)
    assert v_sku is not None
    assert v_sku['sku_id'] == 'VIEW-SKU1'
    assert v_sku['gross_margin'] == Decimal('1200.00')

    # 3. Query vw_catalog_master
    v_mst = await db_conn.fetchrow("SELECT * FROM vw_catalog_master WHERE sku_internal_id = $1;", s_id)
    assert v_mst is not None
    assert v_mst['product_code'] == 'AH-VIEW-01'
    assert v_mst['sku_id'] == 'VIEW-SKU1'
    assert v_mst['gross_margin'] == Decimal('1200.00')
    assert v_mst['shopdeck_sku_id'] == 'SD-VIEW-SKU'
    assert v_mst['shopdeck_product_id'] == 'SD-VIEW-PRD'
