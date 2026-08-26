from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict

class MemoryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: Optional[str] = None
    tags: List[str] = []

class MemoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    metadata: Dict[str, Any]

class MemoryProvider(ABC):
    """
    Abstract interface for Aaram Brain Core memory retention.
    Provides logical read/write boundaries independent of the underlying database technology.
    """
    
    @abstractmethod
    async def read_memory(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Retrieve memory entries matching the logical query."""
        pass

    @abstractmethod
    async def write_memory(self, entry: MemoryEntry, session_id: Optional[str] = None) -> None:
        """Persist a memory entry to the intelligence state."""
        pass
