"""
AZM Seed Script — Initialize DB and Ingest Catalog Namespace

Convenience script for development bootstrap.
Runs: azm_init → catalog_ingester

Usage:
    python -m src.azm.azm_seed_catalog [--db-url sqlite:///azm_knowledge.db]
"""
import argparse
import sys

from src.azm.azm_init import init_azm_db
from src.azm.ingestion.catalog_ingester import ingest_catalog


def seed(db_url: str = None) -> None:
    print("=" * 60)
    print("AZM Seed — Initialize + Ingest Catalog Namespace")
    print("=" * 60)

    print("\n[1/2] Initializing AZM database...")
    init_azm_db(db_url)

    print("\n[2/2] Ingesting Catalog BS...")
    result = ingest_catalog(db_url)
    print(f"  Status : {result['status']}")
    print(f"  Message: {result['message']}")

    if result["status"] == "FAILED":
        print("\nSeed FAILED.", file=sys.stderr)
        sys.exit(1)

    print("\nAZM Seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap AZM with Catalog namespace.")
    parser.add_argument("--db-url", default=None, help="Override AZM_DATABASE_URL")
    args = parser.parse_args()
    seed(args.db_url)
