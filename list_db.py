import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev")
    rows = await conn.fetch("""
        SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'p')
    """)
    for r in rows:
        print(r['relname'])
    await conn.close()

asyncio.run(run())
