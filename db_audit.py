import asyncio
import asyncpg
import sys

URL_LEGACY = "postgresql://postgres:postgres@localhost:5434/aarambooks_brain_core_dev"
URL_NEW = "postgresql://postgres:postgres@localhost:5434/shopdeck_bs_prod"

CANDIDATES = [
    "vw_shopdeck_shipment_ndr_reports",
    "vw_shopdeck_ndr_action_log",
    "shipment_ndr_reports",
    "ndr_action_log"
]

async def check_db():
    try:
        conn = await asyncpg.connect(URL_LEGACY)
    except Exception as e:
        print("Failed to connect to legacy DB:", e)
        # fallback to postgres just in case
        try:
            conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5434/postgres")
        except Exception as e2:
            print("Failed fallback:", e2)
            return

    version = await conn.fetchval('SELECT version()')
    db_name = await conn.fetchval('SELECT current_database()')
    print(f"DATABASE: {db_name}")
    print(f"VERSION: {version}")
    
    for obj in CANDIDATES:
        print(f"\n--- OBJECT: {obj} ---")
        row = await conn.fetchrow('''
            SELECT n.nspname as schema, c.relname as name, c.relkind as type, pg_get_userbyid(c.relowner) as owner, c.oid
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = $1
        ''', obj)
        if not row:
            print(f"NOT FOUND")
            continue
            
        print(f"SCHEMA: {row['schema']}, TYPE: {row['type']}, OWNER: {row['owner']}, OID: {row['oid']}")
        oid = row['oid']
        
        # Definitions if view
        if row['type'] == 'v':
            def_view = await conn.fetchval('SELECT pg_get_viewdef($1)', oid)
            print("DEFINITION:")
            print(def_view)
            
        # Dependencies from pg_depend
        deps = await conn.fetch('''
            SELECT classid::regclass, objid, objsubid, deptype
            FROM pg_depend
            WHERE refobjid = $1
        ''', oid)
        
        print("DEPENDENCIES (objects depending on this):")
        for d in deps:
            # Look up object name
            if d['classid'] == 'pg_class':
                name = await conn.fetchval('SELECT relname FROM pg_class WHERE oid = $1', d['objid'])
                print(f"  pg_class: {name} (type: {d['deptype']})")
            elif d['classid'] == 'pg_rewrite':
                name = await conn.fetchval('SELECT rulename FROM pg_rewrite WHERE oid = $1', d['objid'])
                print(f"  pg_rewrite: {name} (type: {d['deptype']})")
            elif d['classid'] == 'pg_constraint':
                name = await conn.fetchval('SELECT conname FROM pg_constraint WHERE oid = $1', d['objid'])
                print(f"  pg_constraint: {name} (type: {d['deptype']})")
            else:
                print(f"  {d['classid']}: {d['objid']} (type: {d['deptype']})")
                
        # Dependencies TO pg_depend (what this depends on)
        deps_on = await conn.fetch('''
            SELECT refclassid::regclass, refobjid, deptype
            FROM pg_depend
            WHERE objid = $1
        ''', oid)
        print("DEPENDS ON:")
        for d in deps_on:
            if d['refclassid'] == 'pg_class':
                name = await conn.fetchval('SELECT relname FROM pg_class WHERE oid = $1', d['refobjid'])
                print(f"  pg_class: {name}")
            elif d['refclassid'] == 'pg_namespace':
                name = await conn.fetchval('SELECT nspname FROM pg_namespace WHERE oid = $1', d['refobjid'])
                print(f"  pg_namespace: {name}")
            else:
                pass

        # Indexes / Constraints
        indexes = await conn.fetch('''
            SELECT indexrelid::regclass as idx
            FROM pg_index
            WHERE indrelid = $1
        ''', oid)
        if indexes:
            print("INDEXES:", [i['idx'] for i in indexes])
            
        # Row count for parity
        if row['type'] in ('r', 'v'):
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{obj}"')
            print(f"ROW_COUNT: {count}")

    await conn.close()

    print("\n--- DATA PARITY ---")
    try:
        conn_leg = await asyncpg.connect(URL_LEGACY)
        conn_new = await asyncpg.connect(URL_NEW)
        
        for t in ["shipment_ndr_reports", "ndr_action_log"]:
            c_leg = await conn_leg.fetchval(f'SELECT COUNT(*) FROM "{t}"')
            c_new = await conn_new.fetchval(f'SELECT COUNT(*) FROM "{t}"')
            print(f"{t} COUNT - Legacy: {c_leg}, New: {c_new}")
            
            # Latest timestamp
            if t == "shipment_ndr_reports":
                max_leg = await conn_leg.fetchval('SELECT MAX(latest_ndr_time) FROM shipment_ndr_reports')
                max_new = await conn_new.fetchval('SELECT MAX(latest_ndr_time) FROM shipment_ndr_reports')
                print(f"  MAX_TIME - Legacy: {max_leg}, New: {max_new}")
            if t == "ndr_action_log":
                max_leg = await conn_leg.fetchval('SELECT MAX(action_time) FROM ndr_action_log')
                max_new = await conn_new.fetchval('SELECT MAX(action_time) FROM ndr_action_log')
                print(f"  MAX_TIME - Legacy: {max_leg}, New: {max_new}")

        await conn_leg.close()
        await conn_new.close()
    except Exception as e:
        print("Parity check error:", e)

asyncio.run(check_db())
