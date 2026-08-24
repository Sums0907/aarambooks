from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.shared.config import settings

engine = create_async_engine(settings.database_url, echo=(settings.environment == "development"))
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# TODO: Add pgvector extension configuration and vector types in later milestones.
