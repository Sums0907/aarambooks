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

from src.shared.memory_contracts import SuspendedExecutionState, SuspendedActionStatus
from src.shared.evidence_request_contracts import AbstractEvidenceRequest

class SuspendedActionRecord(Base):
    __tablename__ = "core_suspended_actions"
    
    nonce = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    request_data = Column(JSONB, nullable=False)
    status = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
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

    async def write_memory(self, entry: MemoryEntry, session_id: Optional[str] = None, ttl_seconds: Optional[int] = None) -> None:
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

    async def suspend_action(self, state: SuspendedExecutionState, ttl_seconds: int) -> None:
        async with self.session_factory() as session:
            record = SuspendedActionRecord(
                nonce=state.nonce,
                session_id=state.session_id,
                request_data=state.request.model_dump(mode="json"),
                status=state.status.value,
                expires_at=state.expires_at
            )
            session.add(record)
            await session.commit()

    async def retrieve_suspended_action(self, nonce: str, session_id: str) -> Optional[SuspendedExecutionState]:
        from sqlalchemy import select
        from datetime import datetime, timezone
        
        async with self.session_factory() as session:
            stmt = select(SuspendedActionRecord).where(
                SuspendedActionRecord.nonce == nonce,
                SuspendedActionRecord.session_id == session_id
            )
            result = await session.execute(stmt)
            record = result.scalars().first()
            
            if not record:
                return None
                
            # If it's expired but still marked PENDING, we shouldn't return it as active,
            # but returning it so the engine can reject it is fine.
            # Actually, the prompt says "Ensure expired/rejected/consumed actions cannot be consumed."
            # The atomic_consume_action enforces this, but let's also reflect it here.
            
            now = datetime.now(timezone.utc)
            # SQLAlchemy DateTime with timezone might be returned as naive or aware depending on driver.
            # Assuming it's timezone aware.
            expires = record.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
                
            if now > expires and record.status == SuspendedActionStatus.PENDING.value:
                return None # Act as if it doesn't exist or is expired

            req = AbstractEvidenceRequest.model_validate(record.request_data)
            return SuspendedExecutionState(
                nonce=record.nonce,
                session_id=record.session_id,
                request=req,
                status=SuspendedActionStatus(record.status),
                expires_at=expires,
                created_at=record.created_at.replace(tzinfo=timezone.utc) if record.created_at.tzinfo is None else record.created_at
            )

    async def atomic_consume_action(self, nonce: str, session_id: str) -> bool:
        from sqlalchemy import update
        from datetime import datetime, timezone
        
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                update(SuspendedActionRecord)
                .where(
                    SuspendedActionRecord.nonce == nonce,
                    SuspendedActionRecord.session_id == session_id,
                    SuspendedActionRecord.status == SuspendedActionStatus.PENDING.value,
                    SuspendedActionRecord.expires_at > now
                )
                .values(status=SuspendedActionStatus.CONSUMED.value)
            )
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount == 1
