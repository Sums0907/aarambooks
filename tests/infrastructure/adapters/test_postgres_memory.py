import pytest
from unittest.mock import MagicMock
from src.brain_core.memory.interfaces import MemoryEntry, MemoryQuery
from src.infrastructure.adapters.postgres_memory import PgVectorMemoryAdapter, MemoryRecord

@pytest.mark.asyncio
async def test_write_and_read_memory():
    # Setup mock session factory
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    # Create mock record
    mock_record = MemoryRecord(
        session_id="session_123",
        content="The customer prefers email communication",
        metadata_={"tags": ["customer_preference", "contact"]}
    )
    
    mock_result.scalars.return_value.all.return_value = [mock_record]
    
    # Async mock for execute
    async def mock_execute(*args, **kwargs):
        return mock_result
        
    async def mock_commit(*args, **kwargs):
        pass
        
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    
    # Async context manager mock
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    mock_factory = MagicMock(return_value=mock_session_context)
    
    adapter = PgVectorMemoryAdapter(mock_factory)
    
    entry = MemoryEntry(
        content="The customer prefers email communication",
        metadata={"tags": ["customer_preference", "contact"]}
    )
    
    # Write memory
    await adapter.write_memory(entry, session_id="session_123")
    
    # Read memory by session
    query = MemoryQuery(session_id="session_123")
    results = await adapter.read_memory(query)
    
    assert len(results) == 1
    assert results[0].content == "The customer prefers email communication"
    assert "tags" in results[0].metadata

@pytest.mark.asyncio
async def test_read_memory_empty():
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    
    async def mock_execute(*args, **kwargs):
        return mock_result
        
    mock_session.execute = mock_execute
    
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    mock_factory = MagicMock(return_value=mock_session_context)
    adapter = PgVectorMemoryAdapter(mock_factory)
    query = MemoryQuery(session_id="non_existent")
    results = await adapter.read_memory(query)
    assert len(results) == 0
