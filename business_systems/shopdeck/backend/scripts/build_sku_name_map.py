#!/usr/bin/env python3
"""
build_sku_name_map.py

Seeds the `sku_name_map` table in the ShopDeck BS database from the live
Inventory database. This table maps product_name → item_code so that the
sync engine can populate order_line_items.sku_id even when ShopDeck MCP
returns sku_id=null.

Run once, then re-run any time SKUs are added to Inventory:
    python3 build_sku_name_map.py
"""

import asyncio
import asyncpg
import re
import os

SHOPDECK_DB = os.environ.get("DATABASE_URL_SYNC", os.environ.get("DATABASE_URL"))
if not SHOPDECK_DB or "user:password" in SHOPDECK_DB:
    # Local development default fallback (documented here)
    SHOPDECK_DB = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"

INVENTORY_DB = os.environ.get("INVENTORY_DB_URL")
if not INVENTORY_DB:
    # Local development default fallback (documented here)
    INVENTORY_DB = "postgresql://postgres:password@localhost:5433/inventory_dev"


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation/extra spaces for fuzzy-safe exact match."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


async def main():
    inv_conn = await asyncpg.connect(INVENTORY_DB)
    sd_conn = await asyncpg.connect(SHOPDECK_DB)

    # 1. Ensure the mapping table exists in ShopDeck BS DB
    await sd_conn.execute("""
        CREATE TABLE IF NOT EXISTS sku_name_map (
            product_name        TEXT NOT NULL,
            product_name_norm   TEXT NOT NULL,
            item_code           TEXT NOT NULL,
            sku_code            TEXT,
            shopdeck_sku_id     TEXT,
            PRIMARY KEY (product_name_norm)
        );
    """)
    print("✅ sku_name_map table ensured.")

    # 2. Pull all SKUs + product names from Inventory
    rows = await inv_conn.fetch("""
        SELECT s.item_code, s.sku_code, s.shopdeck_sku_id, p.product_name
        FROM skus s
        JOIN products p ON s.product_id = p.id
        WHERE s.status = 'ACTIVE'
    """)
    print(f"   Found {len(rows)} active SKUs in Inventory.")

    # 3. Upsert into ShopDeck BS
    upserted = 0
    for r in rows:
        raw_name = r["product_name"] or ""
        norm = normalize_name(raw_name)
        if not norm:
            continue
        await sd_conn.execute("""
            INSERT INTO sku_name_map (product_name, product_name_norm, item_code, sku_code, shopdeck_sku_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (product_name_norm) DO UPDATE
                SET item_code = EXCLUDED.item_code,
                    sku_code = EXCLUDED.sku_code,
                    shopdeck_sku_id = EXCLUDED.shopdeck_sku_id,
                    product_name = EXCLUDED.product_name
        """, raw_name, norm, r["item_code"], r["sku_code"], r["shopdeck_sku_id"])
        upserted += 1

    print(f"✅ Upserted {upserted} entries into sku_name_map.")

    # 4. Quick verification: how many MCP orders can now be resolved?
    resolvable = await sd_conn.fetchval("""
        SELECT COUNT(DISTINCT oli.order_id)
        FROM order_line_items oli
        JOIN sku_name_map m ON m.product_name_norm = 
            regexp_replace(lower(trim(oli.product_name)), '[^a-z0-9 ]', ' ', 'g')
        WHERE oli.sku_id IS NULL AND oli.product_name IS NOT NULL
    """)
    total_null = await sd_conn.fetchval(
        "SELECT COUNT(*) FROM order_line_items WHERE sku_id IS NULL AND product_name IS NOT NULL"
    )
    print(f"\n📊 Resolution coverage: {resolvable}/{total_null} orders with null sku_id now resolvable via product_name bridge.")

    await inv_conn.close()
    await sd_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
