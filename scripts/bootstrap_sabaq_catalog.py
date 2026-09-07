import asyncio
import csv
import json
import logging
from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.adapters.postgres_sabaq import PostgresSabaqProvider
from src.brain_core.knowledge.interfaces import SabaqProvenance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def bootstrap():
    csv_file = "business_systems/catalog/docs/shopdeck_catalogues.csv"
    provider = PostgresSabaqProvider(AsyncSessionLocal)
    
    count = 0
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                product_code = row.get("Product Code", "")
                sku_id = row.get("Sku Id", "")
                name = row.get("Name", "")
                category = row.get("Product Type", "")
                colour = row.get("Colour", "")
                
                if not product_code:
                    continue
                
                # We synthesise a realistic text prompt that a user might provide
                search_content = f"Product: {name}, Category: {category}, Colour: {colour}, Code: {product_code}, SKU: {sku_id}"
                
                metadata = {
                    "product_type": category,
                    "colour": colour,
                    "product_code": product_code,
                    "sku_id": sku_id,
                    "source_system": "SHOPDECK"
                }
                
                source_ref = f"shopdeck_csv_bootstrap_{product_code}_{sku_id}"
                
                await provider.record_approved_outcome(
                    domain="catalog",
                    search_content=search_content,
                    payload=row,
                    provenance=SabaqProvenance.BUSINESS_SYSTEM_HISTORY,
                    metadata=metadata,
                    source_reference=source_ref
                )
                count += 1
                if count % 50 == 0:
                    logger.info(f"Loaded {count} records...")
                    
        logger.info(f"Successfully bootstrapped {count} ShopDeck catalog records into SABAQ.")
    except Exception as e:
        logger.error(f"Failed to bootstrap SABAQ: {e}")

if __name__ == "__main__":
    asyncio.run(bootstrap())
