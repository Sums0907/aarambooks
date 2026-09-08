from typing import List, Dict, Any, Optional
import asyncpg

class NDRRepository:
    """
    Data access layer for NDR operational data. 
    Strictly isolated boundary: Only this layer knows about internal database tables and raw SQL.
    """
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def check_awb_exists(self, awb_no: str) -> bool:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM order_line_items WHERE awb_no = $1)", awb_no)

    async def is_ndr_table_populated(self) -> bool:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM shipment_ndr_reports)")

    async def get_shipment_ndr_report(self, awb_no: str) -> Optional[Dict[str, Any]]:
        """Fetch the current summary state of a shipment experiencing an NDR."""
        query = """
            SELECT DISTINCT ON (snr.awb_no)
                snr.awb_no, snr.order_status, snr.courier_partner, snr.customer_id, snr.customer_name,
                snr.payment_mode, snr.pickup_time, snr.latest_ndr_time, snr.latest_ndr_reason,
                snr.latest_ofd_time, snr.delivery_time, snr.ndr_count, snr.ofd_count,
                snr.seller_actions, snr.ndr_status,
                ci.customer_number, ci.drop_pincode
            FROM shipment_ndr_reports snr
            LEFT JOIN customer_info ci ON ci.awb_no = snr.awb_no
            WHERE snr.awb_no = $1
            ORDER BY snr.awb_no, snr.ndr_count DESC
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, awb_no)
            return dict(record) if record else None

    async def get_ndr_action_history(self, awb_no: str) -> List[Dict[str, Any]]:
        """Fetch the chronological log of resolution actions taken for a shipment."""
        query = """
            SELECT 
                action_type, action_by, action_time, response_status, 
                response_time, remarks, message_text, reattempt_date, 
                is_priority_escalate, call_duration
            FROM ndr_action_log
            WHERE awb_no = $1
            ORDER BY action_time ASC NULLS LAST
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, awb_no)
            return [dict(r) for r in records]

    async def get_order_items(self, awb_no: str) -> List[Dict[str, Any]]:
        """Fetch the product items and pricing details for the shipment."""
        query = """
            SELECT 
                order_id, createdat, sku_id, customer_sku_short_id, product_name, 
                quantity, selling_price, cod_charge, delivery_fees,
                product_id, customer_product_short_id
            FROM order_line_items
            WHERE awb_no = $1
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, awb_no)
            return [dict(r) for r in records]
