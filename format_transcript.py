import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def run():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['aarambooks_ndr_communications']
    
    eng = await db.customer_engagements.find().sort('created_at', -1).limit(1).to_list(1)
    if not eng: return
    eng_id = eng[0]['engagement_id']
    
    events = await db.customer_engagement_events.find({
        'engagement_id': eng_id, 
        'event_type': 'transcript'
    }).sort('sequence', 1).to_list(None)
    
    out = []
    seen = set()
    for doc in events:
        payload = doc.get('payload', {})
        for ev in payload.get('events', []):
            if ev.get('event_type') == 'transcript':
                data = ev.get('event_data', {})
                for seg in data.get('transcript_segments', []):
                    speaker = seg.get('speaker', 'unknown').upper()
                    text = seg.get('text', '').strip()
                    if text and text not in seen:
                        out.append(f"**{speaker}**: {text}")
                        seen.add(text)

    with open('/Users/sumatidhingra/.gemini/antigravity-ide/brain/b08b6cdf-5af4-4de3-a6dc-db6a34cdabf9/transcript_audit.md', 'w') as f:
        f.write("# Call Transcript Audit\n\n")
        f.write(f"**Engagement ID**: `{eng_id}`\n\n")
        for line in out:
            f.write(line + "\n\n")

asyncio.run(run())
