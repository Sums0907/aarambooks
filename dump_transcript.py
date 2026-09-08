import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
import asyncpg

async def dump():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['aarambooks_ndr_communications']
    
    events = await db.customer_engagement_events.find({'engagement_id': 'eng_e93b4b6c60c25533b1f75c7f910f7775'}).sort('sequence_number', 1).to_list(None)
    for e in events:
        print(f"Role: {e.get('role')} | Content: {e.get('content')} | Sequence: {e.get('sequence_number')} | Subtype: {e.get('event_subtype')}")

    try:
        conn = await asyncpg.connect('postgresql://postgres:shopdeck_pass@localhost:5435/shopdeck_bs_prod')
        res = await conn.fetchrow('SELECT * FROM ndr_intelligence_results WHERE engagement_id = $1', 'eng_e93b4b6c60c25533b1f75c7f910f7775')
        if res:
            print(f"\nWriteback! Action: {res.get('recommended_action')}, Intent: {res.get('customer_intent')}")
            print(f"Diagnosis: {res.get('diagnosis')}")
        else:
            print("\nNo writeback found.")
        await conn.close()
    except Exception as e:
        print(f"PG Error: {e}")

asyncio.run(dump())
