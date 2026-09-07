import asyncio
import csv
import os
from datetime import datetime, timedelta, UTC
from src.infrastructure.mongo_client import get_mongo_db, MongoDBManager

async def generate_atr():
    """
    Generates a CSV report of all NDR resolutions from the past 24 hours.
    This report (Action Taken Report) is used for manual entry into the ShopDeck SaaS.
    """
    await MongoDBManager.connect()
    db = await get_mongo_db()
    collection = db["customer_interactions"]

    yesterday = datetime.now(UTC) - timedelta(days=1)
    
    # Query interactions that have a resolved outcome within the last 24h
    cursor = collection.find({
        "direction": "inbound",
        "metadata.resolved_outcome": {"$exists": True},
        "timestamp": {"$gte": yesterday}
    }).sort("timestamp", -1)

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"NDR_Action_Taken_Report_{datetime.now().strftime('%Y-%m-%d')}.csv"
    filepath = os.path.join(reports_dir, filename)

    records_written = 0
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "AWB Number", "Channel", "Customer Reply", "Detected Intent", "Target Date", "Address Notes", "Action To Take (ShopDeck)"])

        async for doc in cursor:
            outcome = doc["metadata"]["resolved_outcome"]
            writer.writerow([
                doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                doc["awb_no"],
                doc["channel"],
                doc["content"],
                outcome.get("intent", "UNKNOWN"),
                outcome.get("reschedule_date", ""),
                outcome.get("address_notes", ""),
                outcome.get("action_to_take", "")
            ])
            records_written += 1

    await MongoDBManager.disconnect()
    print(f"✅ Generated daily ATR: {filepath} ({records_written} records)")

if __name__ == "__main__":
    asyncio.run(generate_atr())
