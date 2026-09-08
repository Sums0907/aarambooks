import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def parse():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['aarambooks_ndr_communications']
    
    # get latest
    eng = await db.customer_engagements.find().sort('created_at', -1).limit(1).to_list(1)
    if not eng: return
    eng_id = eng[0]['engagement_id']
    print(f"Engagement: {eng_id}")
    
    # get transcript events
    events = await db.customer_engagement_events.find({
        'engagement_id': eng_id, 
        'event_type': 'transcript'
    }).sort('sequence', 1).to_list(None)
    
    for doc in events:
        payload = doc.get('payload', {})
        for ev in payload.get('events', []):
            if ev.get('event_type') == 'transcript':
                data = ev.get('event_data', {})
                for seg in data.get('transcript_segments', []):
                    speaker = seg.get('speaker', 'unknown').upper()
                    text = seg.get('text', '')
                    print(f"[{speaker}]: {text}")

asyncio.run(parse())
