"""
Catalog BS Database & System Configuration
Self-contained configuration for Catalog Business System.
"""

import os

CATALOG_DATABASE_URL = os.environ.get(
    "CATALOG_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5434/catalog_bs_dev"
)

# Idempotency deduplication window in seconds (24 hours)
IDEMPOTENCY_TTL_SECONDS = int(os.environ.get("CATALOG_IDEMPOTENCY_TTL_SECONDS", 86400))

# ShopDeck Default Placeholder Quantity for CSV Upload
DEFAULT_SHOPDECK_UPLOAD_QUANTITY = int(os.environ.get("SHOPDECK_UPLOAD_QUANTITY", 10))
