import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, func, JSON, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, or_, cast, true
from src.infrastructure.database import Base
from src.brain_core.knowledge.interfaces import (
    SabaqProvider, 
    SabaqEvidence, 
    SabaqProvenance
)


class SabaqEvidenceRecord(Base):
    __tablename__ = "sabaq_evidence"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_namespace = Column(String, nullable=False, index=True)
    provenance = Column(String, nullable=False)
    evidence_version = Column(Integer, nullable=False, default=1)
    search_content = Column(String, nullable=False)
    structured_payload = Column(JSONB, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    source_reference = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PostgresSabaqProvider(SabaqProvider):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def retrieve_evidence(
        self, 
        domain: str, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None, 
        limit: int = 5
    ) -> List[SabaqEvidence]:
        async with self.session_factory() as session:
            stmt = select(SabaqEvidenceRecord).where(SabaqEvidenceRecord.domain_namespace == domain)
            
            if filters:
                # Handle provenance_in as a proper SQL IN clause on the provenance column
                provenance_in = filters.get("provenance_in")
                if provenance_in:
                    # Accept both enum values and raw strings
                    prov_values = [
                        p.value if hasattr(p, "value") else str(p)
                        for p in provenance_in
                    ]
                    stmt = stmt.where(SabaqEvidenceRecord.provenance.in_(prov_values))
                # All other filters are metadata key lookups
                for k, v in filters.items():
                    if k == "provenance_in":
                        continue
                    stmt = stmt.where(SabaqEvidenceRecord.metadata_[k].astext == str(v))
            
            # FTS Search
            if query:
                search_condition = text("to_tsvector('english', search_content) @@ plainto_tsquery('english', :q)")
                stmt = stmt.where(search_condition)
                rank = text("ts_rank(to_tsvector('english', search_content), plainto_tsquery('english', :q)) DESC")
                stmt = stmt.order_by(rank).params(q=query)
            else:
                stmt = stmt.order_by(SabaqEvidenceRecord.created_at.desc())
                
            stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            return [
                SabaqEvidence(
                    id=r.id,
                    domain_namespace=r.domain_namespace,
                    provenance=SabaqProvenance(r.provenance),
                    evidence_version=r.evidence_version,
                    search_content=r.search_content,
                    structured_payload=r.structured_payload,
                    metadata=r.metadata_,
                    source_reference=r.source_reference,
                    created_at=r.created_at,
                    updated_at=r.updated_at
                ) for r in records
            ]

    async def get_evidence(self, id: str) -> Optional[SabaqEvidence]:
        async with self.session_factory() as session:
            stmt = select(SabaqEvidenceRecord).where(SabaqEvidenceRecord.id == id)
            result = await session.execute(stmt)
            r = result.scalars().first()
            if not r:
                return None
            return SabaqEvidence(
                id=r.id,
                domain_namespace=r.domain_namespace,
                provenance=SabaqProvenance(r.provenance),
                evidence_version=r.evidence_version,
                search_content=r.search_content,
                structured_payload=r.structured_payload,
                metadata=r.metadata_,
                source_reference=r.source_reference,
                created_at=r.created_at,
                updated_at=r.updated_at
            )
    async def record_approved_outcome(
        self, 
        domain: str, 
        search_content: str, 
        payload: Dict[str, Any], 
        provenance: SabaqProvenance, 
        metadata: Optional[Dict[str, Any]] = None,
        source_reference: Optional[str] = None
    ) -> str:
        
        if provenance not in (SabaqProvenance.HUMAN_APPROVED_DECISION, SabaqProvenance.BUSINESS_SYSTEM_HISTORY, SabaqProvenance.DERIVED_PROFILE):
            val = provenance.value if hasattr(provenance, 'value') else str(provenance)
            raise ValueError(f"Invalid provenance for long-term evidence: {val}")
            
        async with self.session_factory() as session:
            if source_reference:
                stmt = select(SabaqEvidenceRecord).where(
                    SabaqEvidenceRecord.domain_namespace == domain,
                    SabaqEvidenceRecord.source_reference == source_reference
                )
                result = await session.execute(stmt)
                existing = result.scalars().first()
                if existing:
                    existing.search_content = search_content
                    existing.structured_payload = payload
                    existing.metadata_ = metadata or {}
                    existing.provenance = provenance.value
                    existing.evidence_version += 1
                    await session.commit()
                    return existing.id
            
            new_id = str(uuid.uuid4())
            record = SabaqEvidenceRecord(
                id=new_id,
                domain_namespace=domain,
                provenance=provenance.value,
                search_content=search_content,
                structured_payload=payload,
                metadata_=metadata or {},
                source_reference=source_reference
            )
            session.add(record)
            await session.commit()
            return new_id
