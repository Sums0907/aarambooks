import asyncio
import asyncpg
import json

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev")
    rows = await conn.fetch("SELECT engagement_id, state, awb_no, call_context FROM customer_engagements WHERE awb_no = '142285240356604'")
    for row in rows:
        print(f"Engagement ID: {row['engagement_id']}, State: {row['state']}, AWB: {row['awb_no']}")
    if not rows:
        print("No engagement found for AWB 142285240356604")
        
    print("\nChecking latest engagement states:")
    rows = await conn.fetch("SELECT engagement_id, awb_no, state, created_at FROM customer_engagements ORDER BY created_at DESC LIMIT 5")
    for row in rows:
        print(f"[{row['created_at']}] Engagement ID: {row['engagement_id']}, State: {row['state']}, AWB: {row['awb_no']}")
        
    await conn.close()

asyncio.run(main())
