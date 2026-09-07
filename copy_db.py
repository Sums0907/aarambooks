import asyncio
import asyncpg
from business_systems.shopdeck.backfill import CORE_TABLES

SRC_DB = "postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev"
DST_DB = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"

async def copy_table(pool_src, pool_dst, table_name):
    async with pool_src.acquire() as conn_src:
        rows = await conn_src.fetch(f'SELECT * FROM "{table_name}"')
        if not rows:
            print(f"Table {table_name} is empty in source.")
            return

        col_names = list(rows[0].keys())
        col_names_str = ", ".join(f'"{c}"' for c in col_names)
        placeholders_str = ", ".join(f"${i+1}" for i in range(len(col_names)))
        insert_sql = f'INSERT INTO "{table_name}" ({col_names_str}) VALUES ({placeholders_str}) ON CONFLICT DO NOTHING'
        
        records = [tuple(r.values()) for r in rows]
        
        async with pool_dst.acquire() as conn_dst:
            try:
                await conn_dst.executemany(insert_sql, records)
                print(f"✅ Copied {len(records)} to {table_name}.")
            except Exception as e:
                print(f"❌ Failed for {table_name}: {e}")

async def run():
    pool_src = await asyncpg.create_pool(SRC_DB)
    pool_dst = await asyncpg.create_pool(DST_DB)
    
    # Process only the first 9 tables which we know missed the shopdeck_bs_prod target initially
    for t in CORE_TABLES[:9]:
        await copy_table(pool_src, pool_dst, t)
        
    await pool_src.close()
    await pool_dst.close()

asyncio.run(run())
