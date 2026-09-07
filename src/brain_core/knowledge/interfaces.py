from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_text: str
    domain: str
    limit: int = 5

class KnowledgeResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    source: str
    confidence_score: float
    metadata: Dict[str, Any]

class KnowledgeProvider(ABC):
    """
    Abstract interface for Aaram Brain Core ecosystem understanding.
    Provides logical search boundaries independent of specific vector/retrieval implementations.
    """
    
    @abstractmethod
    async def search_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """Retrieve ecosystem understanding relevant to the query."""
        pass

from enum import Enum
from typing import Optional
from datetime import datetime

class SabaqProvenance(Enum):
    BUSINESS_SYSTEM_HISTORY = "BUSINESS_SYSTEM_HISTORY"
    HUMAN_APPROVED_DECISION = "HUMAN_APPROVED_DECISION"
    DERIVED_PROFILE = "DERIVED_PROFILE"

class SabaqEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    domain_namespace: str
    provenance: SabaqProvenance
    evidence_version: int = 1
    search_content: str
    structured_payload: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_reference: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SabaqProvider(ABC):
    @abstractmethod
    async def retrieve_evidence(self, domain: str, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[SabaqEvidence]:
        pass

    @abstractmethod
    async def get_evidence(self, id: str) -> Optional[SabaqEvidence]:
        """Fetch an exact SabaqEvidence record by its primary key ID."""
        pass

    @abstractmethod
    async def record_approved_outcome(self, domain: str, search_content: str, payload: Dict[str, Any], provenance: SabaqProvenance, metadata: Optional[Dict[str, Any]] = None, source_reference: Optional[str] = None) -> str:
        pass
