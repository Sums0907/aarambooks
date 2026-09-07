import asyncio
import asyncpg
import os

async def main():
    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev",
    ).replace("postgresql+asyncpg://", "postgresql://")
    
    conn = await asyncpg.connect(db_url)
    try:
        # Drop all views
        await conn.execute("DROP VIEW IF EXISTS vw_catalog_master CASCADE;")
        await conn.execute("DROP VIEW IF EXISTS vw_catalog_skus CASCADE;")
        await conn.execute("DROP VIEW IF EXISTS vw_catalog_products CASCADE;")
        
        # Drop all tables in dependency order
        await conn.execute("DROP TABLE IF EXISTS catalog_publication_artifacts CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_channel_mappings CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_price_history CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_sku_id_reservations CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_product_code_reservations CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_skus CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_products CASCADE;")
        await conn.execute("DROP TABLE IF EXISTS catalog_idempotency_records CASCADE;")
        
        with open("business_systems/catalog/schema.sql") as f:
            await conn.execute(f.read())
        with open("business_systems/catalog/public_views.sql") as f:
            await conn.execute(f.read())
        print("Catalog tables wiped and schema reapplied cleanly.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
