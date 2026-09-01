import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import pandas as pd

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/aarambooks"

async def main():
    try:
        engine = create_async_engine(DATABASE_URL)
        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)
        async with SessionLocal() as session:
            result = await session.execute(text("SELECT * FROM warehouses;"))
            rows = result.fetchall()
            if not rows:
                print("No rows found in warehouses table.")
                return
            
            # Print using pandas for nice formatting
            df = pd.DataFrame(rows, columns=result.keys())
            print(df.to_string())
    except Exception as e:
        print(f"Error querying Postgres: {e}")

asyncio.run(main())
