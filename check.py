import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5433/catalog_bs_prod')
    cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'vw_catalog_products'")
    print([c['column_name'] for c in cols])
    await conn.close()
    
asyncio.run(check())
