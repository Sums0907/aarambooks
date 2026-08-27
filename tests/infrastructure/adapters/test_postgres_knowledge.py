import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.infrastructure.database import Base
from src.brain_core.knowledge.interfaces import KnowledgeQuery
from src.infrastructure.adapters.postgres_knowledge import PgVectorKnowledgeAdapter, KnowledgeRecord

# We cannot easily test pgvector type in SQLite memory database directly since Vector is Postgres specific.
# However, for the unit testing phase, we can mock the session or omit the vector column in a specialized test setup,
# OR we can mock the sqlalchemy execution for the adapter.

from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_search_knowledge_mocked():
    # Setup mock session factory
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    # Create mock record
    mock_record = KnowledgeRecord(
        domain="inventory",
        content="Inventory tracking rules",
        source="doc1",
        metadata_={"version": "1.0"}
    )
    
    mock_result.scalars.return_value.all.return_value = [mock_record]
    
    # Async mock for execute
    async def mock_execute(*args, **kwargs):
        return mock_result
        
    mock_session.execute = mock_execute
    
    # Async context manager mock
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    
    mock_factory = MagicMock(return_value=mock_session_context)
    
    adapter = PgVectorKnowledgeAdapter(mock_factory)
    query = KnowledgeQuery(query_text="tracking rules", domain="inventory", limit=1)
    
    results = await adapter.search_knowledge(query)
    
    assert len(results) == 1
    assert results[0].content == "Inventory tracking rules"
    assert results[0].source == "doc1"
    assert results[0].confidence_score == 0.9
