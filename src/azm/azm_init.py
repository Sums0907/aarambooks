"""
AZM Initialization Script

Creates an empty, valid AZM knowledge database with all tables applied.
This script is NAMESPACE-AGNOSTIC — it does not ingest any Business System.
The database is ready to accept ingestion from any BS after running this script.

Usage:
    python -m src.azm.azm_init [--db-url sqlite:///azm_knowledge.db]

AZM INVARIANT: This script does NOT connect to any Business System database.
"""
import argparse
import sys

from src.azm.db import get_connection, execute_schema, is_initialized
from src.azm.config import AZM_DATABASE_URL


def init_azm_db(db_url: str = None) -> None:
    url = db_url or AZM_DATABASE_URL
    print(f"[azm_init] Initializing AZM knowledge database at: {url}")

    conn = get_connection(url)
    try:
        if is_initialized(conn):
            print("[azm_init] Schema already applied (idempotent). No changes made.")
        else:
            execute_schema(conn)
            print("[azm_init] Schema applied successfully.")

        # Verify all expected tables are present
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        expected = {
            "azm_aliases", "azm_attr_mappings", "azm_concepts",
            "azm_external_mappings", "azm_ingestion_runs", "azm_namespaces",
            "azm_provenance", "azm_relationships",
            "azm_schematic_attrs", "azm_schematic_refs",
        }
        missing = expected - set(tables)
        if missing:
            raise RuntimeError(f"Schema incomplete — missing tables: {missing}")

        print(f"[azm_init] Verified {len(expected)} tables present.")
        print("[azm_init] AZM database ready.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the AZM knowledge database.")
    parser.add_argument("--db-url", default=None, help="Override AZM_DATABASE_URL")
    args = parser.parse_args()
    try:
        init_azm_db(args.db_url)
    except Exception as exc:
        print(f"[azm_init] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
