import asyncio
import asyncpg
from business_systems.shopdeck.backfill import CORE_TABLES

DB_URL = "postgresql://postgres:postgres@localhost:5434/postgres"

async def run():
    pool = await asyncpg.create_pool(DB_URL)
    async with pool.acquire() as conn:
        for t in CORE_TABLES:
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{t}"')
                print(f"{t}: {count}")
            except Exception as e:
                print(f"{t}: {e}")
    await pool.close()

asyncio.run(run())
