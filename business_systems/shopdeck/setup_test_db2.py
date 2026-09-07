import asyncio
import asyncpg
import sys

async def setup():
    try:
        conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5434/postgres")
        
        try:
            await conn.execute("DROP DATABASE IF EXISTS shopdeck_test_db")
        except asyncpg.exceptions.ObjectInUseError:
            pass
        
        await conn.execute("CREATE DATABASE shopdeck_test_db")
        await conn.close()
        
        print("Created shopdeck_test_db on 5434")
        
        conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5434/shopdeck_test_db")
        with open("db/internal_tables.sql") as f:
            await conn.execute(f.read())
        with open("db/migrations/001_ndr_queue.sql") as f:
            await conn.execute(f.read())
        with open("db/migrations/002_ndr_queue_hardening.sql") as f:
            await conn.execute(f.read())
        await conn.close()
        print("Migrations applied")
        
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(setup())
