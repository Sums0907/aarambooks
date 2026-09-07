import asyncio
import uuid
import json
import logging
from fastapi.testclient import TestClient

from src.main import app
from src.infrastructure.mongo_client import get_mongo_db
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord, NormalizationStatus
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository

logging.basicConfig(level=logging.INFO)

async def setup_test_engagement(engagement_id: str, action_request_id: str):
    repo = CustomerEngagementRepository()
    db = await get_mongo_db()
    
    record = CustomerEngagementRecord(
        engagement_id=engagement_id,
        action_request_id=action_request_id,
        awb_no="AWB123TEST",
        channel="VOICE",
        provider="EXOTEL",
        call_context={"customer_phone": "9999999999", "awb_no": "AWB123TEST", "customer_name": "Test User"}
    )
    
    # Try to insert directly or update
    doc = record.model_dump()
    doc["normalization_status"] = NormalizationStatus.NOT_READY
    
    await db.customer_engagements.update_one(
        {"engagement_id": engagement_id},
        {"$set": doc},
        upsert=True
    )
    print(f"Test engagement {engagement_id} seeded in MongoDB.")

async def run_webhook_test():
    NAMESPACE_NDR = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    synthetic_queue_id = "test_queue_item_999"
    engagement_id = f"eng_{uuid.uuid5(NAMESPACE_NDR, synthetic_queue_id).hex}"
    action_request_id = f"act_{uuid.uuid5(NAMESPACE_NDR, synthetic_queue_id).hex}"
    
    await setup_test_engagement(engagement_id, action_request_id)
    
    import httpx
    
    payload = {
        "CallSid": "mock_call_sid_123",
        "CustomField": f"{engagement_id}|{action_request_id}"
    }
    
    print("\n--- SIMULATING EXOTEL WEBHOOK ---")
    headers = {
        "Content-Type": "application/json",
        "x-auth-token": "kDWz6cehoTlsJkrV_rv2DLtADr_2b09X_p3hAqFuqYI"  # From .env AARAM_EXOTEL_WEBHOOK_SECRET
    }
    
    # Use AsyncClient to share the same event loop as Motor
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/customer-engagement/voice/exotel/session-start", 
            json=payload,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("PASS: Webhook successfully correlated and returned 200 OK.")
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
            
            # Verify the actual contract
            if "response" in data and "data" in data["response"] and "greeting_message" in data["response"]["data"]:
                print("PASS: Response matches VoiceBot JSON contract!")
            else:
                print("FAIL: Response does not match the expected VoiceBot JSON contract.")
                print(data)
        else:
            print(f"FAIL: Expected 200 OK, got {response.status_code}")
            print(response.text)

        # Test Duplicate Webhook
        print("\n--- SIMULATING DUPLICATE WEBHOOK ---")
        response2 = await client.post(
            "/api/customer-engagement/voice/exotel/session-start", 
            json=payload,
            headers=headers
        )
        
        print(f"Status Code: {response2.status_code}")
        if response2.status_code == 200:
            print("PASS: Duplicate Webhook successfully correlated idempotently and returned 200 OK.")
        else:
            print(f"FAIL: Expected 200 OK on duplicate, got {response2.status_code}")
            print(response2.text)

        # CRASH BOUNDARY TEST
        print("\n--- SIMULATING CRASH BOUNDARY (NO CALL SID PERSISTED) ---")
        crash_queue_id = "test_queue_item_crash"
        crash_engagement_id = f"eng_{uuid.uuid5(NAMESPACE_NDR, crash_queue_id).hex}"
        crash_action_id = f"act_{uuid.uuid5(NAMESPACE_NDR, crash_queue_id).hex}"
        
        # Setup engagement WITHOUT provider_call_id
        await setup_test_engagement(crash_engagement_id, crash_action_id)
        
        crash_payload = {
            "CallSid": "mock_call_sid_crash",
            "CustomField": f"{crash_engagement_id}|{crash_action_id}"
        }
        
        crash_response = await client.post(
            "/api/customer-engagement/voice/exotel/session-start", 
            json=crash_payload,
            headers=headers
        )
        
        print(f"Status Code: {crash_response.status_code}")
        if crash_response.status_code == 200:
            print("PASS: Crash boundary webhook successfully correlated using CustomField despite missing local provider correlation!")
        else:
            print(f"FAIL: Expected 200 OK on crash boundary, got {crash_response.status_code}")
            print(crash_response.text)

if __name__ == "__main__":
    asyncio.run(run_webhook_test())
