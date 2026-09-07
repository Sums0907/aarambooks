"""
Pytest Fixtures for Catalog BS Test Suite
"""

import os
import sys
import pytest
import pytest_asyncio
import asyncpg

# Ensure catalog root is in sys.path
catalog_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if catalog_root not in sys.path:
    sys.path.insert(0, catalog_root)

try:
    from catalog.config import CATALOG_DATABASE_URL
    from catalog.service import CatalogService
except ImportError:
    from config import CATALOG_DATABASE_URL
    from service import CatalogService

@pytest_asyncio.fixture(scope="function")
async def db_conn():
    conn = await asyncpg.connect(CATALOG_DATABASE_URL)
    # Ensure schema is applied
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    await conn.execute(schema_sql)

    tr = conn.transaction()
    await tr.start()
    try:
        yield conn
    finally:
        await tr.rollback()
        await conn.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_database():
    """Truncates all catalog tables before and after each test function for pristine isolation."""
    conn = await asyncpg.connect(CATALOG_DATABASE_URL)
    await conn.execute(
        """
        TRUNCATE TABLE
            catalog_products,
            catalog_skus,
            catalog_sku_id_reservations,
            catalog_product_code_reservations,
            catalog_price_history,
            catalog_channel_mappings,
            catalog_publication_artifacts,
            catalog_idempotency_records
        CASCADE;
        """
    )
    yield
    await conn.execute(
        """
        TRUNCATE TABLE
            catalog_products,
            catalog_skus,
            catalog_sku_id_reservations,
            catalog_product_code_reservations,
            catalog_price_history,
            catalog_channel_mappings,
            catalog_publication_artifacts,
            catalog_idempotency_records
        CASCADE;
        """
    )
    await conn.close()

@pytest_asyncio.fixture(scope="function")
async def catalog_service():
    service = await CatalogService.create(CATALOG_DATABASE_URL)
    yield service
    await service.close()
