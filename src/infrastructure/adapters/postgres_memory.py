import json
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from src.infrastructure.database import Base
from src.brain_core.memory.interfaces import MemoryProvider, MemoryQuery, MemoryEntry

class MemoryRecord(Base):
    __tablename__ = "core_memories"
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(String, nullable=True, index=True)
    content = Column(String, nullable=False)
    tags = Column(ARRAY(String), nullable=False, server_default="{}")
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PgVectorMemoryAdapter(MemoryProvider):
    """
    Adapter that connects Aaram Brain Core memory interface to PostgreSQL.
    Stores and retrieves logical memory entries.
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def read_memory(self, query: MemoryQuery) -> List[MemoryEntry]:
        from sqlalchemy import select
        
        async with self.session_factory() as session:
            stmt = select(MemoryRecord)
            
            if query.session_id:
                stmt = stmt.where(MemoryRecord.session_id == query.session_id)
            
            if query.tags:
                stmt = stmt.where(MemoryRecord.tags.contains(query.tags))
                
            stmt = stmt.order_by(MemoryRecord.created_at.desc())
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            return [
                MemoryEntry(content=r.content, metadata=r.metadata_)
                for r in records
            ]

    async def write_memory(self, entry: MemoryEntry, session_id: Optional[str] = None) -> None:
        async with self.session_factory() as session:
            tags = entry.metadata.get("tags", []) if isinstance(entry.metadata, dict) else []
            record = MemoryRecord(
                session_id=session_id,
                content=entry.content,
                tags=tags,
                metadata_=entry.metadata
            )
            session.add(record)
            await session.commit()
