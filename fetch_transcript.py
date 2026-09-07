import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.aarambooks_ndr_communications
    events = db.customer_engagement_events
    
    # Get all transcript events from the last 15 minutes, sorted by occurred_at
    cursor = events.find({"event_type": "transcript"}).sort("occurred_at", 1).limit(50)
    docs = await cursor.to_list(length=50)
    
    print("\n--- Full Transcript ---")
    for doc in docs:
        payload = doc.get("payload", {})
        
        # Exotel V2 format: payload -> events[0] -> event_data -> transcript_segments
        v2_events = payload.get("events", [])
        if v2_events:
            for ev in v2_events:
                if ev.get("event_type") == "transcript":
                    segments = ev.get("event_data", {}).get("transcript_segments", [])
                    for seg in segments:
                        speaker = seg.get("speaker", "UNKNOWN").upper()
                        text = seg.get("text", "")
                        if text:
                            print(f"[{speaker}]: {text}")
        else:
            # V1 format fallback
            data = payload.get("data", {})
            if data:
                text = data.get("text", "")
                speaker = data.get("speaker", "UNKNOWN").upper()
                if text:
                    print(f"[{speaker}]: {text}")

asyncio.run(main())
