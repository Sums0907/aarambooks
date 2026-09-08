import asyncio
import asyncpg
import argparse
import sys
from motor.motor_asyncio import AsyncIOMotorClient

DB_URI = 'postgresql://postgres:shopdeck_pass@localhost:5435/shopdeck_bs_prod'
MONGO_URI = 'mongodb://localhost:27017'

async def get_fk_dependencies(conn):
    fks = await conn.fetch("""
        SELECT
            tc.table_name AS dependent_table,
            ccu.table_name AS referenced_table
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
    """)
    deps = {}
    for fk in fks:
        dt = fk['dependent_table']
        rt = fk['referenced_table']
        if dt not in deps:
            deps[dt] = set()
        deps[dt].add(rt)
    return deps

def topological_sort(deps, tables):
    # Filter graph to only include our tables
    filtered_deps = {t: set() for t in tables}
    for dt, rts in deps.items():
        if dt in tables:
            filtered_deps[dt] = rts.intersection(set(tables))
            
    # Sort: tables with no dependencies go last in deletion (they are roots)
    # Actually for deletion we want to delete leaves first.
    # A leaf is a table that nothing depends on.
    # So we want to sort such that if A depends on B, A comes before B in the list.
    order = []
    visited = set()
    
    def visit(n):
        if n in visited:
            return
        visited.add(n)
        for d, rts in filtered_deps.items():
            if n in rts: # d depends on n, so d must be deleted before n
                visit(d)
        order.append(n)
        
    for t in tables:
        visit(t)
        
    # Reverse to get deletion order: things that depend on nothing (or were visited first) are at the end of `order`?
    # Wait, the logic: if D depends on R, we must delete D before R.
    # Let's do standard topological sort.
    # directed graph where edge is R -> D (meaning D depends on R)
    # wait, edge D -> R means D depends on R. To delete, we must delete D before R.
    
    del_order = []
    in_degree = {t: 0 for t in tables}
    for d, rts in filtered_deps.items():
        for r in rts:
            in_degree[r] += 1
            
    # queue contains tables that nobody depends on (in_degree == 0). These can be deleted safely.
    q = [t for t in tables if in_degree[t] == 0]
    while q:
        curr = q.pop(0)
        del_order.append(curr)
        # remove edges from curr to its dependencies
        for r in filtered_deps.get(curr, []):
            in_degree[r] -= 1
            if in_degree[r] == 0:
                q.append(r)
                
    if len(del_order) != len(tables):
        raise Exception("Cycle detected in FK graph!")
        
    return del_order

async def run_teardown(dry_run=True):
    print(f"=== TEARDOWN TEST DEBRIS (DRY_RUN={dry_run}) ===")
    
    conn = await asyncpg.connect(DB_URI)
    db_name = await conn.fetchval('SELECT current_database()')
    if db_name != 'shopdeck_bs_prod':
        print(f"FATAL: Connected to {db_name}, expected shopdeck_bs_prod.")
        sys.exit(1)
        
    deps = await get_fk_dependencies(conn)
    tables = ['ndr_intelligence_results', 'ndr_engagements', 'ndr_queue', 'order_line_items', 'customer_info', 'shipment_ndr_reports']
    del_order = topological_sort(deps, tables)
    print(f"\n[Computed Deletion Order]\n{del_order}")

    # First, gather candidate AWBs BEFORE opening the transaction so we can also check Mongo safely?
    # Actually, we do everything inside the transaction for Postgres.
    
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    db = mongo_client["aarambooks_ndr_communications"]
    
    async with conn.transaction():
        print("\n[1] Resolving candidate AWBs (FOR UPDATE)...")
        candidates = await conn.fetch("""
            SELECT DISTINCT awb_no FROM (
                SELECT awb_no FROM ndr_queue 
                WHERE (awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%' OR awb_no LIKE 'AWBGATE3%')
                  AND updated_at < NOW() - INTERVAL '10 minutes'
                UNION
                SELECT awb_no FROM shipment_ndr_reports 
                WHERE (awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%' OR awb_no LIKE 'AWBGATE3%')
                UNION
                SELECT awb_no FROM order_line_items 
                WHERE (awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%' OR awb_no LIKE 'AWBGATE3%')
                UNION
                SELECT awb_no FROM customer_info 
                WHERE (awb_no LIKE 'AWBCERT%' OR awb_no LIKE 'TEST_AWB_%' OR awb_no LIKE 'AWBGATE3%')
            ) AS c
        """)
        awbs = [c['awb_no'] for c in candidates]
        
        # Filter AWBs that have a NEW updated_at in ndr_queue
        # Wait, if an AWB is in ndr_queue with updated_at >= 10 mins ago, we should entirely skip it.
        active = await conn.fetch("""
            SELECT awb_no FROM ndr_queue 
            WHERE awb_no = ANY($1) 
              AND updated_at >= NOW() - INTERVAL '10 minutes'
        """, awbs)
        active_awbs = set(r['awb_no'] for r in active)
        
        awbs = [a for a in awbs if a not in active_awbs]
        print(f"Discovered {len(awbs)} synthetic, inactive AWBs: {awbs}")
        if not awbs:
            print("No test debris found.")
            await conn.close()
            return

        for a in awbs:
            if not (a.startswith('AWBCERT') or a.startswith('TEST_AWB_') or a.startswith('AWBGATE3')):
                raise Exception(f"FATAL: Unsafe AWB discovered in candidate list: {a}")

        print("\n[2] Resolving and locking Postgres dependent IDs (FOR UPDATE)...")
        snr = await conn.fetch("SELECT awb_no FROM shipment_ndr_reports WHERE awb_no = ANY($1) FOR UPDATE", awbs)
        ci = await conn.fetch("SELECT awb_no FROM customer_info WHERE awb_no = ANY($1) FOR UPDATE", awbs)
        oli = await conn.fetch("SELECT awb_no FROM order_line_items WHERE awb_no = ANY($1) FOR UPDATE", awbs)
        nq = await conn.fetch("SELECT queue_item_id FROM ndr_queue WHERE awb_no = ANY($1) FOR UPDATE", awbs)
        q_ids = [r['queue_item_id'] for r in nq]
        
        e_ids = []
        if q_ids:
            ne = await conn.fetch("SELECT engagement_id FROM ndr_engagements WHERE queue_item_id = ANY($1) FOR UPDATE", q_ids)
            e_ids = [r['engagement_id'] for r in ne]
            
        nir_ids = []
        if q_ids or e_ids:
            nir = await conn.fetch("SELECT result_id FROM ndr_intelligence_results WHERE queue_item_id = ANY($1) OR engagement_id = ANY($2) FOR UPDATE", 
                                   q_ids if q_ids else ['dummy'], e_ids if e_ids else ['dummy'])
            nir_ids = [r['result_id'] for r in nir]

        counts = {
            'shipment_ndr_reports': len(snr),
            'customer_info': len(ci),
            'order_line_items': len(oli),
            'ndr_queue': len(nq),
            'ndr_engagements': len(e_ids),
            'ndr_intelligence_results': len(nir_ids)
        }
        for k, v in counts.items():
            print(f"  Locked {v} {k}")

        print("\n[3] Executing Postgres Deletions...")
        for table in del_order:
            if table == 'ndr_intelligence_results' and nir_ids:
                res = await conn.execute("DELETE FROM ndr_intelligence_results WHERE result_id = ANY($1)", nir_ids)
                if int(res.split()[-1]) != len(nir_ids): raise Exception("Count mismatch!")
                print(f"  Deleted {len(nir_ids)} ndr_intelligence_results")
            elif table == 'ndr_engagements' and e_ids:
                res = await conn.execute("DELETE FROM ndr_engagements WHERE engagement_id = ANY($1)", e_ids)
                if int(res.split()[-1]) != len(e_ids): raise Exception("Count mismatch!")
                print(f"  Deleted {len(e_ids)} ndr_engagements")
            elif table == 'ndr_queue' and q_ids:
                res = await conn.execute("DELETE FROM ndr_queue WHERE queue_item_id = ANY($1)", q_ids)
                if int(res.split()[-1]) != len(q_ids): raise Exception("Count mismatch!")
                print(f"  Deleted {len(q_ids)} ndr_queue")
            elif table == 'order_line_items' and awbs:
                res = await conn.execute("DELETE FROM order_line_items WHERE awb_no = ANY($1)", awbs)
                if int(res.split()[-1]) != len(oli): raise Exception("Count mismatch!")
                print(f"  Deleted {len(oli)} order_line_items")
            elif table == 'customer_info' and awbs:
                res = await conn.execute("DELETE FROM customer_info WHERE awb_no = ANY($1)", awbs)
                if int(res.split()[-1]) != len(ci): raise Exception("Count mismatch!")
                print(f"  Deleted {len(ci)} customer_info")
            elif table == 'shipment_ndr_reports' and awbs:
                res = await conn.execute("DELETE FROM shipment_ndr_reports WHERE awb_no = ANY($1)", awbs)
                if int(res.split()[-1]) != len(snr): raise Exception("Count mismatch!")
                print(f"  Deleted {len(snr)} shipment_ndr_reports")

        print("\n[4] Mongo Pre-Delete Verification...")
        # Resolve Mongo IDs
        engs = await db.customer_engagements.find({"awb_no": {"$in": awbs}}).to_list(None)
        m_e_ids = [e["engagement_id"] for e in engs]
        
        event_count = 0
        if m_e_ids:
            event_count = await db.customer_engagement_events.count_documents({"engagement_id": {"$in": m_e_ids}})
            
        print(f"  Resolved {event_count} customer_engagement_events")
        print(f"  Resolved {len(m_e_ids)} customer_engagements")

        print("\n[5] Postgres Verification before COMMIT...")
        remaining = await conn.fetchval("SELECT COUNT(*) FROM ndr_queue WHERE awb_no = ANY($1)", awbs)
        if remaining > 0:
            raise Exception("Verification failed: ndr_queue still contains test AWBs!")

        if dry_run:
            print("\n[DRY RUN] Rolling back transaction.")
            raise Exception("Dry Run - Rollback")
        else:
            print("\n[EXECUTE] Performing Mongo Deletions before Postgres Commit...")
            if m_e_ids:
                res1 = await db.customer_engagement_events.delete_many({"engagement_id": {"$in": m_e_ids}})
                print(f"  Deleted {res1.deleted_count} customer_engagement_events")
                if res1.deleted_count != event_count: raise Exception("Mongo count mismatch for events!")
                
                res2 = await db.customer_engagements.delete_many({"engagement_id": {"$in": m_e_ids}})
                print(f"  Deleted {res2.deleted_count} customer_engagements")
                if res2.deleted_count != len(m_e_ids): raise Exception("Mongo count mismatch for engagements!")
            print("Mongo Deletions Successful. Committing Postgres transaction.")

    # Only reached if not dry_run
    print("Cleanup committed successfully.")
    await conn.close()

async def verify_eligibility():
    print("\n--- POST-COMMIT ELIGIBILITY VERIFICATION ---")
    conn = await asyncpg.connect(DB_URI)
    eligible = await conn.fetch("""
        SELECT snr.awb_no
        FROM (SELECT DISTINCT ON (awb_no, ndr_count) awb_no, ndr_status, order_status, payment_mode, delivery_time FROM shipment_ndr_reports ORDER BY awb_no, ndr_count DESC) snr
        INNER JOIN customer_info ci ON ci.awb_no = snr.awb_no
        WHERE snr.ndr_status = 'pending' AND snr.order_status = 'dispatched' AND snr.payment_mode = 'cod' AND snr.delivery_time IS NULL
        AND (snr.awb_no LIKE 'AWBCERT%' OR snr.awb_no LIKE 'TEST_AWB_%' OR snr.awb_no LIKE 'AWBGATE3%')
    """)
    print(f"Eligible synthetic items found: {len(eligible)}")
    await conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Execute deletion (default is dry-run)')
    args = parser.parse_args()
    
    try:
        asyncio.run(run_teardown(dry_run=not args.execute))
    except Exception as e:
        if str(e) == "Dry Run - Rollback":
            pass
        else:
            print(f"ABORTED: {e}")
            sys.exit(1)
            
    if not args.execute:
        asyncio.run(verify_eligibility())
    else:
        asyncio.run(verify_eligibility())
