import asyncio
import asyncpg
DB_URL = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"
async def run():
    conn = await asyncpg.connect(DB_URL)
    count = await conn.fetchval('SELECT count(*) FROM order_line_items')
    print("COUNT:", count)
    await conn.close()
asyncio.run(run())
