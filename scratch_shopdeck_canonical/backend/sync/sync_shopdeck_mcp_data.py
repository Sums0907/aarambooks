#!/usr/bin/env python3
"""
ShopDeck MCP Data Synchronization Engine
`sync_shopdeck_mcp_data.py`

Decoupled Universal Checkpoint Engine with Independent NDR Proxy.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import asyncpg

try:
    from .mcp_client import ShopDeckMCPClient
    from shopdeck import config
except ImportError:
    from shopdeck.mcp_client import ShopDeckMCPClient
    from shopdeck import config
    import os

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("shopdeck_sync")

DATABASE_URL = config.DATABASE_URL_SYNC.replace("+asyncpg", "")

# Conflict targets / unique constraint definitions for UPSERT
TABLE_PRIMARY_KEYS: Dict[str, List[str]] = {
    "order_summary": ["order_id"],
    "order_line_items": ["order_id", "sku_id"], # Typically PK is composite or awb_no. We assume standard.
    "customer_info": ["awb_no"],
    "shipment_ndr_reports": ["awb_no"],
    "ndr_action_log": ["_id"],
}

# The 8 event tables are explicitly EXCLUDED until ShopDeck provides a unique immutable event ID.
# "cancel_reason_events", "order_cancellation_events", "return_exchange_events",
# "post_order_survey_submit_events", "rating_review_feedback_submit_events",
# "payment_gateway_events", "checkout_external_events", "checkout_input_error_events"

CORE_TABLES = [
    "order_summary",
    "order_line_items",
    "customer_info",
    "ndr_action_log"
]

EVENT_TABLES = [
    "cancel_reason_events", "order_cancellation_events", "return_exchange_events",
    "post_order_survey_submit_events", "rating_review_feedback_submit_events",
    "payment_gateway_events", "checkout_external_events", "checkout_input_error_events"
]


def get_lock_id(namespace: str, unit_name: str) -> int:
    """Generate a stable 64-bit PostgreSQL BIGINT for advisory locking."""
    digest = hashlib.md5(f"{namespace}:{unit_name}".encode('utf-8')).hexdigest()
    return int(digest[:15], 16)


async def ensure_unique_indexes_and_checkpoints(pool: asyncpg.Pool):
    """Ensure unique indexes and checkpoints table exist."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_checkpoints (
                table_name TEXT PRIMARY KEY,
                last_watermark TIMESTAMP WITH TIME ZONE
            );
        """)
        for table, pks in TABLE_PRIMARY_KEYS.items():
            cols_str = ", ".join(f'"{c}"' for c in pks)
            idx_name = f"idx_uq_{table}_{'_'.join(pks)}"
            try:
                await conn.execute(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" ON "{table}" ({cols_str});'
                )
            except Exception as e:
                logger.debug(f"Index creation note for {table}: {e}")


def parse_timestamp(val: Any) -> Optional[datetime]:
    if val is None or val == "":
        return None
    if isinstance(val, dict) and "value" in val:
        val = val["value"]
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        val = val.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    if isinstance(val, datetime):
        return val
    return None


def clean_row_for_postgres(
    row: Dict[str, Any], table_columns: Set[str], col_types: Dict[str, str]
) -> Dict[str, Any]:
    cleaned = {}
    for col, val in row.items():
        if col not in table_columns:
            continue
        data_type = col_types.get(col, "").lower()

        if "timestamp" in data_type or "date" in data_type:
            cleaned[col] = parse_timestamp(val)
        elif data_type in ("json", "jsonb"):
            if isinstance(val, (dict, list)):
                cleaned[col] = json.dumps(val)
            elif isinstance(val, str) and val:
                cleaned[col] = val
            else:
                cleaned[col] = None
        elif isinstance(val, dict) and "value" in val:
            cleaned[col] = val["value"]
        elif isinstance(val, (dict, list)):
            cleaned[col] = json.dumps(val)
        elif val == "":
            cleaned[col] = None
        else:
            cleaned[col] = val
    return cleaned


async def get_table_metadata(conn: asyncpg.Connection, table_name: str) -> Tuple[List[str], Dict[str, str]]:
    rows = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
        """,
        table_name,
    )
    col_names = [r["column_name"] for r in rows]
    col_types = {r["column_name"]: r["data_type"] for r in rows}
    return col_names, col_types


import re as _re

def _normalize_name(name: str) -> str:
    """Normalize product name for fuzzy-safe exact match against sku_name_map."""
    name = name.lower().strip()
    name = _re.sub(r"[^a-z0-9 ]", " ", name)
    name = _re.sub(r"\s+", " ", name).strip()
    return name


async def _resolve_sku_ids(conn: asyncpg.Connection, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For order_line_items rows where sku_id is null, attempt to resolve it
    from the sku_name_map table using normalized product_name matching.
    Non-fatal: rows without a match are returned unchanged.
    """
    try:
        # Check if sku_name_map exists
        exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'sku_name_map' LIMIT 1"
        )
        if not exists:
            return rows

        # Build lookup dict from DB (single query for entire batch)
        map_rows = await conn.fetch("SELECT product_name_norm, item_code FROM sku_name_map")
        name_map = {r["product_name_norm"]: r["item_code"] for r in map_rows}

        resolved = 0
        for row in rows:
            if row.get("sku_id"):
                continue  # Already has a sku_id, skip
            product_name = row.get("product_name") or ""
            if not product_name:
                continue
            norm = _normalize_name(product_name)
            item_code = name_map.get(norm)
            if item_code:
                row["sku_id"] = item_code
                resolved += 1

        if resolved:
            logger.info(f"   🔗 SKU bridge: resolved {resolved}/{len(rows)} sku_ids from product_name map.")
    except Exception as e:
        logger.warning(f"   ⚠️ SKU bridge resolution failed (non-fatal): {e}")
    return rows


async def upsert_records(conn: asyncpg.Connection, table_name: str, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    db_columns, col_types = await get_table_metadata(conn, table_name)
    col_set = set(db_columns)

    cleaned_rows = [clean_row_for_postgres(r, col_set, col_types) for r in rows]

    # SKU bridge: resolve sku_id from product_name when MCP returns null
    if table_name == "order_line_items":
        cleaned_rows = await _resolve_sku_ids(conn, cleaned_rows)

    present_cols = [c for c in db_columns if any(c in r for r in cleaned_rows)]
    if not present_cols:
        logger.warning(f"⚠️ No matching columns for `{table_name}`.")
        return 0

    col_names_str = ", ".join(f'"{c}"' for c in present_cols)
    placeholders_str = ", ".join(f"${i+1}" for i in range(len(present_cols)))

    records = [tuple(r.get(c) for c in present_cols) for r in cleaned_rows]

    staging_table = f"staging_{table_name}_{int(datetime.now().timestamp())}"
    await conn.execute(f'CREATE TEMP TABLE "{staging_table}" (LIKE "{table_name}");')
    staging_insert_sql = f'INSERT INTO "{staging_table}" ({col_names_str}) VALUES ({placeholders_str})'
    await conn.executemany(staging_insert_sql, records)

    pk_cols = TABLE_PRIMARY_KEYS.get(table_name)
    if pk_cols:
        pk_join_conditions = " AND ".join(f't."{pk}" = s."{pk}"' for pk in pk_cols)
        await conn.execute(
            f'DELETE FROM "{table_name}" t USING "{staging_table}" s WHERE {pk_join_conditions};'
        )

    await conn.execute(f'INSERT INTO "{table_name}" ({col_names_str}) SELECT {col_names_str} FROM "{staging_table}";')
    await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}";')

    return len(records)


async def get_checkpoint(conn: asyncpg.Connection, source_name: str, upper_bound: datetime) -> Optional[datetime]:
    val = await conn.fetchval("SELECT last_watermark FROM sync_checkpoints WHERE table_name = $1", source_name)
    if val:
        return val
    # Explicit One-Time Bootstrap Initialization
    bootstrap_val = upper_bound - timedelta(days=config.BOOTSTRAP_LOOKBACK_DAYS)
    logger.info(f"[*] ONE-TIME BOOTSTRAP for {source_name}: establishing initial checkpoint at {bootstrap_val.isoformat()}")
    # We do NOT save it yet; it saves only if the sync succeeds.
    return bootstrap_val


async def set_checkpoint(conn: asyncpg.Connection, source_name: str, watermark: datetime):
    await conn.execute(
        """
        INSERT INTO sync_checkpoints (table_name, last_watermark)
        VALUES ($1, $2)
        ON CONFLICT (table_name) DO UPDATE SET last_watermark = EXCLUDED.last_watermark
        """,
        source_name, watermark
    )


def hash_row(row_tuple: Tuple) -> str:
    parts = []
    for val in row_tuple:
        if val is None:
            parts.append("NULL")
        elif isinstance(val, (dict, list)):
            parts.append(json.dumps(val, sort_keys=True, separators=(',', ':')))
        elif isinstance(val, float):
            parts.append(f"{val:.6f}")
        elif isinstance(val, datetime):
            parts.append(val.isoformat())
        else:
            parts.append(str(val))
    canonical_str = "|".join(parts)
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

async def insert_event_records(conn: asyncpg.Connection, table_name: str, rows: List[Dict[str, Any]], replay_window_start: datetime) -> int:
    if not rows:
        return 0

    db_columns, col_types = await get_table_metadata(conn, table_name)
    col_set = set(db_columns)

    cleaned_rows = [clean_row_for_postgres(r, col_set, col_types) for r in rows]
    incoming_records = [tuple(r.get(c) for c in db_columns) for r in cleaned_rows]
    
    unique_incoming = {}
    for rec in incoming_records:
        fp = hash_row(rec)
        if fp not in unique_incoming:
            unique_incoming[fp] = rec
            
    db_rows = await conn.fetch(f"SELECT * FROM {table_name} WHERE created_at >= $1", replay_window_start)
    db_records = [tuple(r[c] for c in db_columns) for r in db_rows]
    
    existing_fps = {hash_row(rec) for rec in db_records}
    
    new_records = [rec for fp, rec in unique_incoming.items() if fp not in existing_fps]
    
    if not new_records:
        return 0
        
    col_names_str = ", ".join(f'"{c}"' for c in db_columns)
    placeholders_str = ", ".join(f"${i+1}" for i in range(len(db_columns)))
    
    insert_sql = f'INSERT INTO "{table_name}" ({col_names_str}) VALUES ({placeholders_str})'
    await conn.executemany(insert_sql, new_records)
    
    return len(new_records)

def chunk_list(lst: List[Any], n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def process_sync_unit(pool: asyncpg.Pool, client: ShopDeckMCPClient, unit_name: str, cadence_minutes: int, table_name: str):
    """Independent synchronization unit for a core table."""
    upper_bound = datetime.now(timezone.utc)
    lock_id = get_lock_id(config.LOCK_NAMESPACE, unit_name)

    async with pool.acquire() as conn:
        async with conn.transaction():
            locked = await conn.fetchval("SELECT pg_try_advisory_xact_lock($1)", lock_id)
            if not locked:
                logger.info(f"⚠️ [Unit: {unit_name}] Could not acquire advisory lock. Skipping.")
                return

            last_sync_time = await conn.fetchval("SELECT last_watermark FROM sync_checkpoints WHERE table_name = $1", unit_name)
            if last_sync_time and (upper_bound - last_sync_time).total_seconds() < (cadence_minutes * 60):
                logger.debug(f"[Unit: {unit_name}] Skipping sync. Not due yet.")
                return

            checkpoint = await get_checkpoint(conn, unit_name, upper_bound)
            effective_lower_bound = checkpoint - timedelta(minutes=config.CLOCK_SKEW_OVERLAP_MINUTES)
            
            logger.info(f"🔄 [Unit: {unit_name}] Syncing window: >= {effective_lower_bound.isoformat()} AND < {upper_bound.isoformat()}")
            
            # The standard query logic to MCP. Inject exact half-open ISO timestamp boundaries.
            query = f"SELECT * FROM {table_name} WHERE updatedat >= '{effective_lower_bound.isoformat()}' AND updatedat < '{upper_bound.isoformat()}'"
            res = client.query_data(query, table_name)
            rows = res.get("rows", []) if isinstance(res, dict) else []
            
            if rows:
                await upsert_records(conn, table_name, rows)
                
            await set_checkpoint(conn, unit_name, upper_bound)
            logger.info(f"✅ [Unit: {unit_name}] Completed. Synced {len(rows)} records. Checkpoint advanced.")


async def process_ndr_proxy_unit(pool: asyncpg.Pool, client: ShopDeckMCPClient):
    """Independent NDR Proxy synchronization unit reading directly from MCP."""
    unit_name = "ndr_proxy"
    cadence_minutes = config.CADENCE_MINUTES.get(unit_name, 5)
    upper_bound = datetime.now(timezone.utc)
    lock_id = get_lock_id(config.LOCK_NAMESPACE, unit_name)

    async with pool.acquire() as conn:
        async with conn.transaction():
            locked = await conn.fetchval("SELECT pg_try_advisory_xact_lock($1)", lock_id)
            if not locked:
                logger.info(f"⚠️ [Unit: {unit_name}] Could not acquire advisory lock. Skipping.")
                return

            # Note: For NDR proxy, we can track 'ndr_proxy' execution timestamp independently if we want,
            # but we use 'ndr_proxy_order_line_items' as the proxy high-water mark.
            # To track execution cadence, we'll check the OLI proxy checkpoint.
            last_sync_time = await conn.fetchval("SELECT last_watermark FROM sync_checkpoints WHERE table_name = $1", "ndr_proxy_order_line_items")
            if last_sync_time and (upper_bound - last_sync_time).total_seconds() < (cadence_minutes * 60):
                logger.debug(f"[Unit: {unit_name}] Skipping NDR proxy sync. Not due yet.")
                return

            logger.info("=" * 65)
            logger.info(f"🔄 [Unit: {unit_name}] Running Direct-MCP NDR Proxy Engine...")
            
            total_synced = 0
            
            # Proxy 1: order_line_items
            oli_cp = await get_checkpoint(conn, "ndr_proxy_order_line_items", upper_bound)
            oli_effective = oli_cp - timedelta(minutes=config.CLOCK_SKEW_OVERLAP_MINUTES)
            oli_query = f"SELECT awb_no FROM order_line_items WHERE updatedat >= '{oli_effective.isoformat()}' AND updatedat < '{upper_bound.isoformat()}'"
            oli_res = client.query_data(oli_query, "order_line_items", start_date=oli_effective.isoformat().replace('+00:00', 'Z'), end_date=upper_bound.isoformat().replace('+00:00', 'Z'))
            oli_rows = oli_res.get("rows", []) if isinstance(oli_res, dict) else []
            awbs_from_oli = {r["awb_no"] for r in oli_rows if r.get("awb_no")}

            # Proxy 2: ndr_action_log
            ndr_cp = await get_checkpoint(conn, "ndr_proxy_ndr_action_log", upper_bound)
            ndr_effective = ndr_cp - timedelta(minutes=config.CLOCK_SKEW_OVERLAP_MINUTES)
            ndr_query = f"SELECT awb_no FROM ndr_action_log WHERE updatedat >= '{ndr_effective.isoformat()}' AND updatedat < '{upper_bound.isoformat()}'"
            ndr_res = client.query_data(ndr_query, "ndr_action_log", start_date=ndr_effective.isoformat().replace('+00:00', 'Z'), end_date=upper_bound.isoformat().replace('+00:00', 'Z'))
            ndr_rows = ndr_res.get("rows", []) if isinstance(ndr_res, dict) else []
            awbs_from_ndr = {r["awb_no"] for r in ndr_rows if r.get("awb_no")}

            # Combine & Deduplicate AWBs
            affected_awbs = awbs_from_oli.union(awbs_from_ndr)
            logger.info(f"   -> Found {len(affected_awbs)} distinct AWBs needing shipment_ndr_reports updates directly from MCP.")

            # Targeted shipment_ndr_reports fetch
            if affected_awbs:
                awb_list = list(affected_awbs)
                for awb_chunk in chunk_list(awb_list, config.AWB_BATCH_SIZE):
                    in_clause = ", ".join(f"'{awb}'" for awb in awb_chunk)
                    targeted_query = f"SELECT * FROM shipment_ndr_reports WHERE awb_no IN ({in_clause})"
                    
                    # Targeted query MUST have dateRange to pass validation
                    proxy_start = (upper_bound - timedelta(days=90)).isoformat().replace('+00:00', 'Z')
                    ndr_report_res = client.query_data(targeted_query, "shipment_ndr_reports", start_date=proxy_start, end_date=upper_bound.isoformat().replace('+00:00', 'Z'))
                    ndr_report_rows = ndr_report_res.get("rows", []) if isinstance(ndr_report_res, dict) else []
                    
                    if ndr_report_rows:
                        await upsert_records(conn, "shipment_ndr_reports", ndr_report_rows)
                        total_synced += len(ndr_report_rows)
                        try:
                            import httpx, os
                            brain_url = os.environ.get("AARAM_BRAIN_URL")
                            if brain_url:
                                new_awbs = [r["awb_no"] for r in ndr_report_rows if r.get("awb_no")]
                                if new_awbs:
                                    async with httpx.AsyncClient(timeout=5.0) as hc:
                                        await hc.post(f"{brain_url}/events/ndr", json={"awb_nos": new_awbs, "source": "shopdeck_ndr_proxy"})
                        except Exception as e:
                            logger.warning(f"Brain NDR webhook failed (non-fatal): {e}")

            # Advance explicit NDR proxy checkpoints independently
            await set_checkpoint(conn, "ndr_proxy_order_line_items", upper_bound)
            await set_checkpoint(conn, "ndr_proxy_ndr_action_log", upper_bound)

            logger.info(f"✅ [Unit: {unit_name}] Completed. {total_synced} shipment_ndr_reports UPSERTed.")
            logger.info("=" * 65)


async def process_event_sync_unit(pool: asyncpg.Pool, client: ShopDeckMCPClient, unit_name: str, cadence_minutes: int, table_name: str):
    upper_bound = datetime.now(timezone.utc)
    lock_id = get_lock_id(config.LOCK_NAMESPACE, unit_name)

    async with pool.acquire() as conn:
        async with conn.transaction():
            locked = await conn.fetchval("SELECT pg_try_advisory_xact_lock($1)", lock_id)
            if not locked:
                logger.info(f"⚠️ [Unit: {unit_name}] Could not acquire advisory lock. Skipping.")
                return

            last_sync_time = await conn.fetchval("SELECT last_watermark FROM sync_checkpoints WHERE table_name = $1", unit_name)
            if last_sync_time and (upper_bound - last_sync_time).total_seconds() < (cadence_minutes * 60):
                logger.debug(f"[Unit: {unit_name}] Skipping sync. Not due yet.")
                return

            checkpoint = await get_checkpoint(conn, unit_name, upper_bound)
            effective_lower_bound = checkpoint - timedelta(minutes=config.EVENT_REPLAY_WINDOW_MINUTES)
            
            logger.info(f"🔄 [Unit: {unit_name}] Event Sync window: >= {effective_lower_bound.isoformat()} AND < {upper_bound.isoformat()}")
            
            query = f"SELECT * FROM {table_name} WHERE created_at >= '{effective_lower_bound.isoformat()}' AND created_at < '{upper_bound.isoformat()}'"
            res = client.query_data(query, table_name)
            rows = res.get("rows", []) if isinstance(res, dict) else []
            
            inserted = 0
            if rows:
                inserted = await insert_event_records(conn, table_name, rows, effective_lower_bound)
                
            await set_checkpoint(conn, unit_name, upper_bound)
            logger.info(f"✅ [Unit: {unit_name}] Completed. Inserted {inserted} / {len(rows)} new records. Checkpoint advanced.")


async def run_orchestrator():
    """Evaluate and execute independent synchronization units."""
    client = ShopDeckMCPClient()
    pool = await asyncpg.create_pool(DATABASE_URL)
    await ensure_unique_indexes_and_checkpoints(pool)

    # 1. Evaluate Core Table Ingestion Units
    for table_name in CORE_TABLES:
        # Checkpoint unit identity maps directly to table name for basic tables
        cadence = config.CADENCE_MINUTES.get(table_name, 60)
        try:
            await process_sync_unit(pool, client, table_name, cadence, table_name)
        except Exception as e:
            logger.error(f"❌ [Unit: {table_name}] Synchronization failed: {e}")
            # Failure is isolated; loop continues to next unit.

    # 2. Evaluate Independent NDR Proxy Unit
    try:
        await process_ndr_proxy_unit(pool, client)
    except Exception as e:
        logger.error(f"❌ [Unit: ndr_proxy] Synchronization failed: {e}")

    # 3. Evaluate Event Table Units
    for table_name in EVENT_TABLES:
        cadence = config.CADENCE_MINUTES.get(table_name, 60)
        try:
            await process_event_sync_unit(pool, client, table_name, cadence, table_name)
        except Exception as e:
            logger.error(f"❌ [Unit: {table_name}] Synchronization failed: {e}")


    # 4. NDR Queue Enrollment (ShopDeck BS responsibility — runs after each NDR sync)
    try:
        from api.repositories.ndr_queue import NDRQueueRepository
        max_claim_attempts = int(_os.environ.get("SHOPDECK_QUEUE_MAX_CLAIM_ATTEMPTS", 5))
        max_retries = int(_os.environ.get("SHOPDECK_QUEUE_MAX_RETRIES", 2))
        queue_repo = NDRQueueRepository(pool)
        enrolled = await queue_repo.enroll_eligible_ndrs(max_claim_attempts, max_retries)
        terminated = await queue_repo.mark_terminal_ndrs()
        logger.info(f"✅ [NDR Queue] Enrolled {enrolled} new item(s), terminated {terminated} stale item(s)")
    except Exception as e:
        logger.error(f"❌ [NDR Queue] Enrollment failed (non-fatal): {e}")

    await pool.close()


def main():
    parser = argparse.ArgumentParser(description="ShopDeck MCP Data Synchronization Utility")
    parser.parse_args()
    
    asyncio.run(run_orchestrator())


if __name__ == "__main__":
    main()
