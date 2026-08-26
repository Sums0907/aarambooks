from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict

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
