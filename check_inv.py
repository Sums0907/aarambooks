import asyncio
import asyncpg

async def check():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5433/inventory_bs')
        cols = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print("Inventory tables:", [c['table_name'] for c in cols])
        await conn.close()
    except Exception as e:
        print("Error:", e)
        
asyncio.run(check())
