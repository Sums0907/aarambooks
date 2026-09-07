import asyncio
import logging
from src.main import ndr_poller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def main():
    print("==================================================")
    print("INITIATING FIRST CONTROLLED PHYSICAL CALL")
    print("==================================================")
    
    logging.info("Starting one manual iteration of the NDR Queue Poller...")
    
    processed = await ndr_poller.process_next_item()
    
    if processed:
        print("\n✅ SUCCESS: Poller claimed an eligible item, registered the engagement, and dispatched the physical Exotel call!")
    else:
        print("\n❌ QUEUE EMPTY: No eligible items found in the ShopDeck NDR Queue.")

if __name__ == "__main__":
    asyncio.run(main())
