import pytest
from typing import List, Optional
from src.brain_core.memory.interfaces import MemoryProvider, MemoryQuery, MemoryEntry

class MockMemoryProvider(MemoryProvider):
    def __init__(self):
        self.entries = []

    async def read_memory(self, query: MemoryQuery) -> List[MemoryEntry]:
        return [e for e in self.entries if not query.tags or any(t in query.tags for t in e.metadata.get("tags", []))]

    async def write_memory(self, entry: MemoryEntry, session_id: Optional[str] = None) -> None:
        self.entries.append(entry)

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
