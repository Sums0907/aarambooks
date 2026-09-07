import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from src.brain_core.knowledge.interfaces import SabaqProvenance
from src.infrastructure.adapters.postgres_sabaq import PostgresSabaqProvider, SabaqEvidenceRecord
from src.infrastructure.database import AsyncSessionLocal, Base, engine




@pytest.mark.asyncio
async def test_domain_isolation():
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    # Mock return for catalog search
    mock_record_catalog = SabaqEvidenceRecord(
        id="123",
        domain_namespace="catalog",
        provenance="HUMAN_APPROVED_DECISION",
        evidence_version=1,
        metadata_={},
        search_content="blue bedsheet",
        structured_payload={"dummy": "catalog_data"}
    )
    
    mock_result.scalars.return_value.all.return_value = [mock_record_catalog]
    
    async def mock_execute(*args, **kwargs):
        return mock_result
        
    mock_session.execute = mock_execute
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    mock_factory = MagicMock(return_value=mock_session_context)
    
    provider = PostgresSabaqProvider(mock_factory)
    
    catalog_results = await provider.retrieve_evidence("catalog", "bedsheet")
    assert len(catalog_results) == 1
    assert catalog_results[0].domain_namespace == "catalog"
    assert catalog_results[0].structured_payload["dummy"] == "catalog_data"

@pytest.mark.asyncio
async def test_provenance_validation():
    mock_factory = MagicMock()
    provider = PostgresSabaqProvider(mock_factory)
    
    # AI Guesses should be rejected
    with pytest.raises(ValueError, match="Invalid provenance for long-term evidence: AI_PROPOSAL"):
        await provider.record_approved_outcome(
            domain="catalog",
            search_content="test",
            payload={},
            provenance="AI_PROPOSAL"
        )

@pytest.mark.asyncio
async def test_metadata_filters_and_persistence():
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    async def mock_execute(*args, **kwargs): return mock_result
    async def mock_commit(*args, **kwargs): pass
    
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    mock_factory = MagicMock(return_value=mock_session_context)
    
    provider = PostgresSabaqProvider(mock_factory)
    
    # Test valid insertion
    await provider.record_approved_outcome(
        domain="catalog",
        search_content="item 1",
        payload={"id": 1},
        provenance=SabaqProvenance.BUSINESS_SYSTEM_HISTORY,
        metadata={"colour": "blue"}
    )
    
    assert mock_session.add.call_count == 1
    added_record = mock_session.add.call_args[0][0]
    assert added_record.domain_namespace == "catalog"
    assert added_record.provenance == "BUSINESS_SYSTEM_HISTORY"

@pytest.mark.asyncio
async def test_duplicate_bootstrap_idempotency():
    mock_session = MagicMock()
    mock_result = MagicMock()
    
    # Simulate existing record
    mock_existing = SabaqEvidenceRecord(
        id="123",
        domain_namespace="catalog",
        provenance="BUSINESS_SYSTEM_HISTORY",
        evidence_version=1,
        search_content="item",
        structured_payload={"name": "v1"},
        metadata_={},
        source_reference="hash123"
    )
    
    mock_result.scalars.return_value.first.return_value = mock_existing
    
    async def mock_execute(*args, **kwargs): return mock_result
    async def mock_commit(*args, **kwargs): pass
    
    mock_session.execute = mock_execute
    mock_session.commit = mock_commit
    
    mock_session_context = MagicMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None
    mock_factory = MagicMock(return_value=mock_session_context)
    
    provider = PostgresSabaqProvider(mock_factory)
    
    id1 = await provider.record_approved_outcome(
        domain="catalog",
        search_content="item updated",
        payload={"name": "v2"},
        provenance=SabaqProvenance.BUSINESS_SYSTEM_HISTORY,
        source_reference="hash123"
    )
    
    assert id1 == "123"
    assert mock_existing.structured_payload["name"] == "v2"
    assert mock_existing.evidence_version == 2
