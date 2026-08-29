import pytest
from typing import List, Optional
from src.brain_core.memory.interfaces import MemoryProvider, MemoryQuery, MemoryEntry
from src.shared.memory_contracts import SuspendedExecutionState, SuspendedActionStatus
class MockMemoryProvider(MemoryProvider):
    def __init__(self):
        self.entries = []
        self.suspended_actions = {}
        self.consumed_nonces = set()

    async def read_memory(self, query: MemoryQuery) -> List[MemoryEntry]:
        return [e for e in self.entries if not query.tags or any(t in query.tags for t in e.metadata.get("tags", []))]

    async def write_memory(self, entry: MemoryEntry, session_id: Optional[str] = None, ttl_seconds: Optional[int] = None) -> None:
        self.entries.append(entry)

    async def suspend_action(self, state: SuspendedExecutionState, ttl_seconds: int) -> None:
        self.suspended_actions[state.nonce] = state

    async def retrieve_suspended_action(self, nonce: str, session_id: str) -> Optional[SuspendedExecutionState]:
        action = self.suspended_actions.get(nonce)
        if action and action.session_id == session_id:
            return action
        return None

    async def atomic_consume_action(self, nonce: str, session_id: str) -> bool:
        if nonce in self.consumed_nonces:
            return False
        action = await self.retrieve_suspended_action(nonce, session_id)
        if action:
            self.consumed_nonces.add(nonce)
            return True
        return False

@pytest.mark.asyncio
async def test_memory_interfaces_can_be_mocked():
    provider = MockMemoryProvider()
    entry = MemoryEntry(content="test memory", metadata={"tags": ["test"]})
    await provider.write_memory(entry, session_id="session-1")
    
    results = await provider.read_memory(MemoryQuery(tags=["test"]))
    assert len(results) == 1
    assert results[0].content == "test memory"

def test_memory_models_are_frozen():
    entry = MemoryEntry(content="test", metadata={})
    with pytest.raises(Exception):
        entry.content = "changed"
