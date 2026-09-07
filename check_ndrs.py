import asyncio
import asyncpg

async def main():
    awbs = ["142285240356604", "24699810620701", "372194722212", "142285241663445"]
    try:
        conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod")
        for awb in awbs:
            row = await conn.fetchrow("SELECT awb_no, latest_ndr_time, latest_ndr_reason FROM shipment_ndr_reports WHERE awb_no = $1", awb)
            if row:
                print(f"✅ FOUND in DB: AWB {awb} (Time: {row['latest_ndr_time']}, Reason: {row['latest_ndr_reason']})")
            else:
                print(f"❌ MISSING in DB: AWB {awb}")
        await conn.close()
    except Exception as e:
        print("DB Error:", e)

asyncio.run(main())
