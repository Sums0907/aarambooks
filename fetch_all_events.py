import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.aarambooks_ndr_communications
    events = db.customer_engagement_events
    
    # Get all transcript events from the last 15 minutes
    cursor = events.find({"event_type": "transcript"}).sort("occurred_at", -1).limit(10)
    docs = await cursor.to_list(length=10)
    
    for doc in reversed(docs):
        eng_id = doc.get("engagement_id")
        call_sid = doc.get("provider_session_id")
        payload = doc.get("payload", {})
        data = payload.get("data", {})
        text = data.get("text", "")
        speaker = data.get("speaker", "UNKNOWN")
        print(f"[{speaker}]: {text} (EngID: {eng_id}, SID: {call_sid})")

asyncio.run(main())
