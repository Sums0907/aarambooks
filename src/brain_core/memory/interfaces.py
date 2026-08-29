from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict
from src.shared.memory_contracts import SuspendedExecutionState

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
    async def write_memory(self, entry: MemoryEntry, session_id: Optional[str] = None, ttl_seconds: Optional[int] = None) -> None:
        """Persist a memory entry to the intelligence state."""
        pass

    @abstractmethod
    async def suspend_action(self, state: SuspendedExecutionState, ttl_seconds: int) -> None:
        """Persist a suspended action awaiting confirmation."""
        pass

    @abstractmethod
    async def retrieve_suspended_action(self, nonce: str, session_id: str) -> Optional[SuspendedExecutionState]:
        """Retrieve a suspended action if it exists and belongs to the session."""
        pass

    @abstractmethod
    async def atomic_consume_action(self, nonce: str, session_id: str) -> bool:
        """Atomically mark a suspended action as consumed. Returns True if successful, False if already consumed or invalid."""
        pass
