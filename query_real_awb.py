import asyncio
import asyncpg

async def check():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod')
        
        ndr_row = await conn.fetchrow("SELECT awb_no FROM shipment_ndr_reports LIMIT 1")
        if not ndr_row:
            print("No NDR reports found!")
            await conn.close()
            return
            
        awb = ndr_row['awb_no']
        print(f"Found real AWB: {awb}")
        
        oli = await conn.fetchrow("SELECT * FROM order_line_items WHERE awb_no = $1", awb)
        if oli:
            print(f"Product Name: {oli['product_name']}")
            print(f"SKU: {oli['sku_id']}")
            print(f"Product ID: {oli['product_id']}")
        
        await conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

asyncio.run(check())
