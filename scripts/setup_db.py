import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.infrastructure.database import Base
from src.infrastructure.adapters.postgres_sabaq import SabaqEvidenceRecord
import os

async def main():
    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql+asyncpg://postgres:postgres@localhost:5434/aarambooks_brain_core_dev",
    ).replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")

if __name__ == "__main__":
    asyncio.run(main())
