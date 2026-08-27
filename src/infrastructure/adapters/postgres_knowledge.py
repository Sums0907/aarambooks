from typing import List
from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from src.infrastructure.database import Base
from src.brain_core.knowledge.interfaces import KnowledgeProvider, KnowledgeQuery, KnowledgeResult

class KnowledgeRecord(Base):
    __tablename__ = "core_knowledge"
    
    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    domain = Column(String, nullable=False, index=True)
    content = Column(String, nullable=False)
    source = Column(String, nullable=False)
    embedding = Column(Vector(768)) # Default size for many models
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PgVectorKnowledgeAdapter(KnowledgeProvider):
    """
    Adapter that connects Aaram Brain Core knowledge interface to PostgreSQL pgvector.
    Provides logical search over ecosystem understanding.
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def search_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        from sqlalchemy import select
        
        async with self.session_factory() as session:
            # Note: A real implementation would compute the embedding of query.query_text
            # using an embedding model before searching pgvector.
            # Since Brain Core is currently isolated from direct SDKs, the embedding 
            # might be generated via the Gateway or another abstract service.
            # For this MVP phase 7 binding, we simulate the retrieval query structure
            # and fallback to a text-like search or just matching domain for now if embedding is missing,
            # but ideally we would do:
            # stmt = select(KnowledgeRecord).where(KnowledgeRecord.domain == query.domain).order_by(KnowledgeRecord.embedding.cosine_distance(query_embedding)).limit(query.limit)
            
            stmt = select(KnowledgeRecord).where(KnowledgeRecord.domain == query.domain).limit(query.limit)
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            return [
                KnowledgeResult(
                    content=r.content,
                    source=r.source,
                    confidence_score=0.9, # Simulated confidence
                    metadata=r.metadata_
                )
                for r in records
            ]
