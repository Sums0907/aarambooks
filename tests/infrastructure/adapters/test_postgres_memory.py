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

from datetime import datetime, timezone, timedelta
from src.shared.memory_contracts import SuspendedExecutionState, SuspendedActionStatus
from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding, ConversationalIntent
from src.infrastructure.adapters.postgres_memory import SuspendedActionRecord

@pytest.mark.asyncio
async def test_suspend_action():
    mock_session = MagicMock()
    async def mock_commit(*args, **kwargs): pass
    mock_session.commit = mock_commit
    
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    adapter = PgVectorMemoryAdapter(MagicMock(return_value=mock_session_context))
    
    req = AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(original_query="", intent=ConversationalIntent.ACTION),
            components=[]
        )
    )
    
    state = SuspendedExecutionState(
        nonce="nonce_123",
        session_id="sess_123",
        request=req,
        status=SuspendedActionStatus.PENDING,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    
    await adapter.suspend_action(state, 300)
    assert mock_session.add.call_count == 1
    added_record = mock_session.add.call_args[0][0]
    assert added_record.nonce == "nonce_123"
    assert added_record.status == "PENDING"

@pytest.mark.asyncio
async def test_atomic_consume_action_success():
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    
    async def mock_execute(*args, **kwargs): return mock_result
    async def mock_commit(*args, **kwargs): pass
    
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    adapter = PgVectorMemoryAdapter(MagicMock(return_value=mock_session_context))
    
    result = await adapter.atomic_consume_action("nonce_123", "sess_123")
    assert result is True

@pytest.mark.asyncio
async def test_atomic_consume_action_failure():
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0  # e.g., expired or already consumed
    
    async def mock_execute(*args, **kwargs): return mock_result
    async def mock_commit(*args, **kwargs): pass
    
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    adapter = PgVectorMemoryAdapter(MagicMock(return_value=mock_session_context))
    
    result = await adapter.atomic_consume_action("nonce_invalid", "sess_123")
    assert result is False
