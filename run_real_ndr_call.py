import asyncio
import httpx
import json
import sys

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_real_ndr_call.py <AWB_NO>")
        print("Example: python3 run_real_ndr_call.py 370909749714")
        sys.exit(1)
        
    awb_no = sys.argv[1]
    brain_url = "http://127.0.0.1:8000"
    
    print("==================================================")
    print("🔥 [LEGACY_MANUAL_DIAGNOSTIC] INITIATING REAL NDR PIPELINE")
    print("==================================================")
    print(f"Target AWB: {awb_no}")
    print("\nWARNING: This tool is deprecated for production. The new architecture uses the NDR Queue.")
    print("The Brain will fetch from ShopDeck, fetch from Inventory,")
    print("build the exact CCC, and trigger the Exotel API to make")
    print("a real outbound phone call to the customer phone number")
    print("registered against this AWB in ShopDeck.")
    print("\nPress Enter to proceed or Ctrl+C to abort...")
    print("\n[1] Bypassing DB corruption. The orchestrator will fetch from VPS and use TEST_PHONE_OVERRIDE from .env for Exotel.")

    print("\n[2] Pushing AWB to Brain's real /events/ndr endpoint...")
    try:
        payload = {"awb_nos": [awb_no], "source": "manual_trigger"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{brain_url}/events/ndr",
                json=payload,
                timeout=300.0  # Increased timeout for LLM CCC building
            )
            print(f"Brain API HTTP Status: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            
            if response.status_code == 200:
                print("\n✅ Webhook accepted by Brain.")
                print("The EventBus is now routing this to the NDR Orchestrator in the background.")
                print("Exotel will initiate the call to the customer shortly.")
            else:
                print("\n❌ Brain rejected the webhook.")
                
    except Exception as e:
        print(f"❌ Failed to reach Brain Backend: {repr(e)}")

if __name__ == "__main__":
    asyncio.run(main())
