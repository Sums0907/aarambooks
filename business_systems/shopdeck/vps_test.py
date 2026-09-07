import asyncio
import httpx
import uuid
from typing import Dict, Any
from api.dependencies import get_db_pool
import asyncpg
import json
import os

async def get_system_token():
    # In the container, we can just use the system token or generate one if needed.
    # For now, we will use direct repository access for Postgres tests, and httpx for API tests.
    pass

async def main():
    print("==================================================")
    print("VPS RUNTIME VERIFICATION SCRIPT")
    print("==================================================")
    
    # 1. VPS API HEALTH
    print("\n[1] VERIFYING VPS API HEALTH")
    api_base = "http://localhost:8210"  # Since we are running inside the container
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{api_base}/api/v1/system/status")
            print(f"REQUEST: GET {api_base}/api/v1/system/status")
            print(f"HTTP STATUS: {resp.status_code}")
            print(f"RESPONSE SUMMARY: {resp.json()}")
            print("PERSISTENCE RESULT: N/A")
    except Exception as e:
        print(f"FAILED to reach VPS API: {e}")

    # 2. REAL SHOPDECK POSTGRES CONNECTIVITY
    print("\n[2] VERIFYING REAL SHOPDECK POSTGRES CONNECTIVITY")
    pool = None
    try:
        db_url = os.environ.get("DATABASE_URL", "postgresql://shopdeck_user:shopdeck_pass@shopdeck-postgres:5432/shopdeck_db")
        pool = await asyncpg.create_pool(db_url)
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version();")
            print(f"Connected to PostgreSQL. Version: {version[:50]}...")
    except Exception as e:
        print(f"FAILED to connect to Postgres: {e}")
        return

    # IMPORT REPOSITORY
    from api.repositories.ndr_queue import NDRQueueRepository
    repo = NDRQueueRepository(pool)
    
    synthetic_awb = f"TEST_AWB_{uuid.uuid4().hex[:8]}"
    
    print("\n[3] SEEDING SYNTHETIC RECORDS")
    async with pool.acquire() as conn:
        
        await conn.execute("""
            INSERT INTO shipment_ndr_reports (awb_no, customer_name, ndr_count)
            VALUES ($1, 'TEST CUSTOMER', 1)
        """, synthetic_awb)

        # Create 4 synthetic NDR events for history test
        queue_item_ids = []
        for i in range(1, 5):
            row = await conn.fetchrow("""
                INSERT INTO ndr_queue (awb_no, queue_status, ndr_attempt_seq, payment_mode, ndr_time_at_enroll, ndr_reason_at_enroll, ndr_count_at_enroll)
                VALUES ($1, 'eligible', $2, 'prepaid', NOW(), 'Customer Unavailable', 1)
                RETURNING queue_item_id
            """, synthetic_awb, i)
            queue_item_ids.append(str(row['queue_item_id']))
    print(f"Created 4 synthetic queue items for AWB {synthetic_awb}: {queue_item_ids}")

    # 4. NDR QUEUE CLAIM & LOCKING
    print("\n[4] VERIFYING QUEUE CLAIM & LOCKING")
    claimer_id = "test_worker_1"
    item1 = await repo.claim_next_eligible(claimer_id, 300)
    print(f"Claimed item: {item1['queue_item_id']} for AWB {item1['awb_no']}")
    
    # Try to claim the same item with another worker (should not get it)
    item2 = await repo.claim_next_eligible("test_worker_2", 300)
    if item2 and item2['queue_item_id'] == item1['queue_item_id']:
        print("FAIL: Locking failed, worker 2 claimed the same item!")
    else:
        print("PASS: Queue claim locking verified.")

    # 5. ENGAGEMENT REGISTRATION
    print("\n[5] VERIFYING ENGAGEMENT REGISTRATION")
    engagement_id = f"eng_{uuid.uuid4().hex[:8]}"
    idem_key = f"idem_{uuid.uuid4().hex[:8]}"
    reg_result = await repo.register_engagement_atomic(str(item1['queue_item_id']), engagement_id, idem_key, claimer_id)
    print(f"Engagement Registration Result: {reg_result}")
    
    # Idempotency / Duplicate test
    dup_reg = await repo.register_engagement_atomic(str(item1['queue_item_id']), f"eng_{uuid.uuid4().hex[:8]}", idem_key, claimer_id)
    print(f"Duplicate Engagement Registration Result (same idem key): {dup_reg}")

    # 6. ATOMIC INTELLIGENCE + ACTION_READY WRITEBACK
    print("\n[6] VERIFYING ATOMIC INTELLIGENCE + ACTION_READY")
    result_id = f"res_{uuid.uuid4().hex[:8]}"
    intel_data = {
        "result_id": result_id,
        "queue_item_id": str(item1['queue_item_id']),
        "engagement_id": engagement_id,
        "awb_no": item1['awb_no'],
        "recommended_action": "REATTEMPT",
        "diagnosis": "Customer wants tomorrow",
        "customer_intent": "RESCHEDULE",
        "confidence_level": "HIGH",
        "provenance": "test",
        "action_parameters": {},
        "reasoning": "test reasoning",
        "risk_score": 1,
        "source_evidence": [],
        "submitted_by": "test"
    }
    intel_res = await repo.persist_intelligence_atomic(intel_data, claimer_id)
    print(f"Intelligence Persistence Result: {intel_res}")
    
    # Duplicate intelligence test
    dup_intel = await repo.persist_intelligence_atomic(intel_data, claimer_id)
    print(f"Duplicate Intelligence Persistence Result: {dup_intel}")

    async with pool.acquire() as conn:
        q_row = await conn.fetchrow("SELECT queue_status FROM ndr_queue WHERE queue_item_id = $1", item1['queue_item_id'])
        print(f"Final Queue Status: {q_row['queue_status']}")

    # 7. FOUR INDEPENDENT SYNTHETIC NDR HISTORIES
    print("\n[7] VERIFYING FOUR INDEPENDENT HISTORIES")
    for i, q_id in enumerate(queue_item_ids[1:], start=2): # Process the remaining 3
        c_item = await repo.claim_next_eligible(claimer_id, 300)
        e_id = f"eng_{uuid.uuid4().hex[:8]}"
        await repo.register_engagement_atomic(str(c_item['queue_item_id']), e_id, f"idem_{uuid.uuid4().hex[:8]}", claimer_id)
        
        r_id = f"res_{uuid.uuid4().hex[:8]}"
        intel_data["result_id"] = r_id
        intel_data["queue_item_id"] = str(c_item['queue_item_id'])
        intel_data["engagement_id"] = e_id
        await repo.persist_intelligence_atomic(intel_data, claimer_id)
        
    async with pool.acquire() as conn:
        histories = await conn.fetch("""
            SELECT q.queue_item_id, q.queue_status, e.engagement_id, ir.result_id
            FROM ndr_queue q
            JOIN ndr_engagements e ON q.queue_item_id = e.queue_item_id
            JOIN ndr_intelligence_results ir ON e.engagement_id = ir.engagement_id
            WHERE q.awb_no = $1
            ORDER BY q.created_at ASC
        """, synthetic_awb)
        
        for idx, h in enumerate(histories, 1):
            print(f"EVENT {idx}: queue_item_id={h['queue_item_id']} -> engagement_id={h['engagement_id']} -> result_id={h['result_id']} -> queue_status={h['queue_status']}")

    print("\n==================================================")
    print("VPS RUNTIME VERIFICATION COMPLETE")
    print("==================================================")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
