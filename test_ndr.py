import asyncio
from src.main import receiver

async def main():
    print("Running _route_ndr...")
    try:
        await receiver._route_ndr({"awb_no": "142285240356604", "source": "manual_trigger"})
        print("Done!")
    except Exception as e:
        print(f"CRASH: {e}")

asyncio.run(main())
