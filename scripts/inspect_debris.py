import asyncio
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def inspect():
    print("--- POSTGRES SCHEMA AND DEBRIS INSPECTION ---")
    conn = await asyncpg.connect('postgresql://postgres:shopdeck_pass@localhost:5435/shopdeck_bs_prod')
    
    # Check FK constraints
    print("\n[Foreign Key Constraints]")
    fks = await conn.fetch("""
        SELECT
            tc.table_name, kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
          AND tc.table_name IN ('ndr_intelligence_results', 'ndr_queue', 'customer_info', 'order_line_items', 'shipment_ndr_reports');
    """)
    if not fks:
        print("No foreign keys found among these tables.")
    for fk in fks:
        print(f"{fk['table_name']}.{fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")

    # Find candidates
    print("\n[Candidate AWBs]")
    candidates = await conn.fetch("""
        SELECT DISTINCT awb_no FROM (
            SELECT awb_no FROM ndr_queue WHERE awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%'
            UNION
            SELECT awb_no FROM shipment_ndr_reports WHERE awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%'
            UNION
            SELECT awb_no FROM order_line_items WHERE awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%'
            UNION
            SELECT awb_no FROM customer_info WHERE awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%'
        ) AS c;
    """)
    awbs = [c['awb_no'] for c in candidates]
    print(f"Found {len(awbs)} candidate AWBs: {awbs}")
    
    # Check eligible counts
    print("\n[Eligibility Check]")
    eligible = await conn.fetch("""
        SELECT snr.awb_no
        FROM (SELECT DISTINCT ON (awb_no, ndr_count) awb_no, ndr_status, order_status, payment_mode, delivery_time FROM shipment_ndr_reports ORDER BY awb_no, ndr_count DESC) snr
        INNER JOIN customer_info ci ON ci.awb_no = snr.awb_no
        WHERE snr.ndr_status = 'pending' AND snr.order_status = 'dispatched' AND snr.payment_mode = 'cod' AND snr.delivery_time IS NULL
        AND (snr.awb_no LIKE 'AWBCERT%' OR snr.awb_no LIKE 'TEST_AWB_%')
    """)
    print(f"Eligible from source (without queue dup check): {len(eligible)}")
    
    await conn.close()

    print("\n--- MONGO DEBRIS INSPECTION ---")
    mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = mongo_client["brain_core"]
    
    engs = await db.customer_engagements.find({"awb_no": {"$in": awbs}}).to_list(None)
    eng_ids = [e["engagement_id"] for e in engs]
    print(f"Found {len(eng_ids)} customer_engagements: {eng_ids}")
    
    events = await db.customer_engagement_events.find({"engagement_id": {"$in": eng_ids}}).to_list(None)
    print(f"Found {len(events)} customer_engagement_events for these engagements.")

if __name__ == '__main__':
    asyncio.run(inspect())
