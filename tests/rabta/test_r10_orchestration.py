import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
)
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding, ConversationalResponse, ConversationalResponseType
from src.brain_core.memory.interfaces import MemoryQuery, MemoryEntry

@pytest.fixture
def mock_classifier():
    classifier = AsyncMock()
    classifier.classify.return_value = ClassifiedRequirement(
        understanding=ConversationalUnderstanding(original_query="test", intent="RETRIEVE", components=[]),
        components=[]
    )
    return classifier

@pytest.fixture
def mock_id_provider():
    provider = AsyncMock()
    provider.extract_understanding.return_value = ConversationalUnderstanding(original_query="test", intent="RETRIEVE", components=[])
    provider.interpret_evidence.return_value = ConversationalResponse(
        response_type=ConversationalResponseType.SUCCESS,
        message="FINAL_ANSWER"
    )
    return provider

@pytest.fixture
def mock_cem_adapter():
    adapter = AsyncMock()
    adapter.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"data": "success"}
    )
    return adapter

@pytest.fixture
def mock_memory_provider():
    provider = AsyncMock()
    provider.read_memory.return_value = []
    return provider

@pytest.fixture
def orchestrator(mock_id_provider, mock_cem_adapter, mock_classifier, mock_memory_provider):
    id_resolver = MagicMock()
    id_resolver.resolve.return_value = mock_id_provider
    
    cem_resolver = MagicMock()
    cem_resolver.resolve.return_value = mock_cem_adapter
    
    return RabtaOrchestrator(
        id_resolver=id_resolver,
        cem_resolver=cem_resolver,
        classifier=mock_classifier,
        memory_provider=mock_memory_provider
    )

@pytest.mark.asyncio
async def test_memory_is_loaded_and_passed(orchestrator, mock_memory_provider, mock_id_provider):
    import uuid
    from src.shared.memory_contracts import ConversationTurn
    
    turn = ConversationTurn(
        turn_id=str(uuid.uuid4()),
        session_id="session-1",
        user_utterance="hello",
        system_response=ConversationalResponse(response_type=ConversationalResponseType.SUCCESS, message="hi")
    )
    
    mock_memory_provider.read_memory.return_value = [
        MemoryEntry(content=turn.model_dump_json(), metadata={"tags": ["ConversationTurn"], "timestamp": turn.timestamp.isoformat()})
    ]
    
    await orchestrator.process_query("test query", "id", "cem", "auth", session_id="session-1")
    
    # Verify memory was read for this session
    mock_memory_provider.read_memory.assert_called_once()
    query = mock_memory_provider.read_memory.call_args[0][0]
    assert isinstance(query, MemoryQuery)
    assert query.session_id == "session-1"
    
    # Verify it was passed to ID
    mock_id_provider.extract_understanding.assert_called_once()
    kwargs = mock_id_provider.extract_understanding.call_args[1]
    assert "history" in kwargs
    assert len(kwargs["history"]) == 1
    assert kwargs["history"][0].turn_id == turn.turn_id

@pytest.mark.asyncio
async def test_memory_is_saved_after_success(orchestrator, mock_memory_provider):
    await orchestrator.process_query("test query", "id", "cem", "auth", session_id="session-1")
    
    mock_memory_provider.write_memory.assert_called_once()
    entry = mock_memory_provider.write_memory.call_args[0][0]
    session_id = mock_memory_provider.write_memory.call_args[1].get("session_id")
    
    assert session_id == "session-1"
    assert "FINAL_ANSWER" in entry.content
    assert "evidence_data" not in entry.content

@pytest.mark.asyncio
async def test_stateless_fallback_on_memory_error(orchestrator, mock_memory_provider, mock_id_provider):
    mock_memory_provider.read_memory.side_effect = Exception("DB Down")
    
    # Should not crash, should just pass empty history
    result = await orchestrator.process_query("test query", "id", "cem", "auth", session_id="session-1")
    
    assert getattr(result, "message", None) == "FINAL_ANSWER"
    kwargs = mock_id_provider.extract_understanding.call_args[1]
    assert kwargs["history"] == []
