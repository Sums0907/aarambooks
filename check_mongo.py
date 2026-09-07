import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.aarambooks_ndr_communications
    engagements = db.customer_engagements
    docs = await engagements.find({"awb_no": "142285240356604"}).to_list(length=10)
    for doc in docs:
        print(f"Engagement ID: {doc.get('engagement_id')}, Status: {doc.get('status')}")
    
    if not docs:
        print("No engagements found!")
        
    print("\nRecent events:")
    events = db.customer_engagement_events
    recent_events = await events.find().sort("occurred_at", -1).limit(5).to_list(length=5)
    for event in recent_events:
        print(f"Event: {event.get('event_type')}, Session ID: {event.get('provider_session_id')}, Eng ID: {event.get('engagement_id')}")

asyncio.run(main())
