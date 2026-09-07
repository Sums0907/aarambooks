import asyncio
import asyncpg
import datetime

async def main():
    import os
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is required")
    conn = await asyncpg.connect(db_url)
    # Reset checkpoints to 1 day ago
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    await conn.execute("UPDATE sync_checkpoints SET last_watermark = $1 WHERE table_name IN ('ndr_proxy_order_line_items', 'ndr_proxy_ndr_action_log')", dt)
    print("Checkpoints reset!")
    await conn.close()

asyncio.run(main())
