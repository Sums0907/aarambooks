import asyncio
import asyncpg
from business_systems.shopdeck.backfill import CORE_TABLES

DB_URL = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"

async def check():
    conn = await asyncpg.connect(DB_URL)
    results = []
    for t in CORE_TABLES:
        try:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{t}"')
            results.append({"table": t, "count": count})
        except Exception as e:
            results.append({"table": t, "error": str(e)})
            
    awb_row = await conn.fetchrow('SELECT awb_no FROM shipment_ndr_reports LIMIT 1')
    awb = awb_row['awb_no'] if awb_row else None
    
    ndr_row = await conn.fetchrow('SELECT awb_no FROM ndr_action_log LIMIT 1')
    ndr_awb = ndr_row['awb_no'] if ndr_row else None
    
    print("DB_RESULTS:")
    for r in results:
        print(r)
    print(f"Sample AWB: {awb}")
    print(f"Sample AWB with Action Log: {ndr_awb}")
    await conn.close()

asyncio.run(check())
