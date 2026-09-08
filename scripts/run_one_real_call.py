import argparse
import asyncio
import logging
from src.main import ndr_poller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_one(use_staging: bool):
    if use_staging:
        # Swap in a staging-targeted adapter explicitly, at the call site, rather than
        # relying on ambient env config someone has to remember to set correctly. See
        # ExotelVoiceBotAdapter.__init__ - this raises immediately if the staging flow URL
        # isn't configured, rather than silently dispatching to production.
        from src.infrastructure.adapters.customer_engagement.exotel_adapter import ExotelVoiceBotAdapter
        ndr_poller.comm_engine.executor.exotel_adapter = ExotelVoiceBotAdapter(use_staging=True)
        logger.warning("STAGING MODE: this call will target the staging bot's flow, not production.")
    else:
        logger.warning("PRODUCTION MODE: this call will target the production bot's flow. Pass --staging to target the staging bot instead.")

    logger.info("Executing ONE physical NDR queue item...")
    result = await ndr_poller.process_next_item()
    if result:
        logger.info("Successfully processed one item!")
    else:
        logger.info("No items were eligible or successfully processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch one real NDR queue item to a physical call.")
    parser.add_argument(
        "--staging", action="store_true",
        help="Target the staging bot's Exotel flow instead of production. Requires "
             "EXOTEL_VOICEBOT_FLOW_URL_STAGING to be configured.",
    )
    args = parser.parse_args()
    asyncio.run(run_one(use_staging=args.staging))
