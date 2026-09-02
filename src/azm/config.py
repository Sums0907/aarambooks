"""
AZM (Aaram Zameer) — Persistent Database Configuration

AZM_DATABASE_URL controls the database backend.
Default: SQLite file in the project root (development).
Production: set to a PostgreSQL URL via environment variable.
"""
import os

# Database connection
AZM_DATABASE_URL: str = os.environ.get(
    "AZM_DATABASE_URL",
    "sqlite:///azm_knowledge.db"
)

# Source contract paths (relative to project root)
AZM_CATALOG_SEMANTIC_CONTRACT_PATH: str = (
    "business_systems/catalog/public-contracts/catalog-semantic-public-contract.md"
)
AZM_CATALOG_SCHEMATIC_CONTRACT_PATH: str = (
    "business_systems/catalog/public_views.sql"
)

# Catalog namespace constants
CATALOG_NAMESPACE_NAME: str = "catalog"
CATALOG_NAMESPACE_CLASSIFICATION: str = "AARAM_NATIVE"
CATALOG_CONTRACT_VERSION: str = "1.1"
