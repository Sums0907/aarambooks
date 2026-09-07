import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.aarambooks_ndr_communications
    events = db.customer_engagement_events
    
    # Get latest session-start event
    session_start = await events.find_one({"event_type": "session-start"}, sort=[("occurred_at", -1)])
    if session_start:
        print(f"\n--- LATEST SESSION-START ---")
        print(json.dumps(session_start.get("payload", {}), indent=2))
        print(f"EngID: {session_start.get('engagement_id')}")
        print(f"CallSid: {session_start.get('provider_session_id')}")

    # Get latest transcript event
    transcript = await events.find_one({"event_type": "transcript"}, sort=[("occurred_at", -1)])
    if transcript:
        print(f"\n--- LATEST TRANSCRIPT ---")
        print(json.dumps(transcript.get("payload", {}), indent=2))
        print(f"EngID: {transcript.get('engagement_id')}")
        print(f"CallSid: {transcript.get('provider_session_id')}")

asyncio.run(main())
