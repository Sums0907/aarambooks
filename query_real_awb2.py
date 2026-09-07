import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod')
    oli = await conn.fetch("SELECT product_name, sku_id, product_id FROM order_line_items LIMIT 5")
    for r in oli:
        print(dict(r))
    await conn.close()

asyncio.run(check())
