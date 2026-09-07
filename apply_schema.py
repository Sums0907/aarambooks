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
        await conn.execute("DROP VIEW IF EXISTS vw_catalog_master CASCADE;")
        await conn.execute("DROP VIEW IF EXISTS vw_catalog_skus CASCADE;")
        await conn.execute("DROP VIEW IF EXISTS vw_catalog_products CASCADE;")
        
        with open("business_systems/catalog/schema.sql") as f:
            await conn.execute(f.read())
        with open("business_systems/catalog/public_views.sql") as f:
            await conn.execute(f.read())
        print("Catalog schema applied.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
