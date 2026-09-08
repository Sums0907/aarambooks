import asyncio
import logging
from src.main import ndr_poller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_one():
    logger.info("Executing ONE physical NDR queue item...")
    result = await ndr_poller.process_next_item()
    if result:
        logger.info("Successfully processed one item!")
    else:
        logger.info("No items were eligible or successfully processed.")

if __name__ == "__main__":
    asyncio.run(run_one())
