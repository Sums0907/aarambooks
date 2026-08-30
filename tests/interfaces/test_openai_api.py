import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.interfaces.openai_api import get_rabta_orchestrator

@pytest.fixture
def mock_orchestrator():
    return AsyncMock()

@pytest.fixture
def client(mock_orchestrator):
    # Override the dependency to inject our mock
    app.dependency_overrides[get_rabta_orchestrator] = lambda: mock_orchestrator
    
    # Also set it on app state as a fallback in case tests invoke routing differently
    app.state.rabta_orchestrator = mock_orchestrator
    
    with TestClient(app) as client:
        yield client
        
    app.dependency_overrides.clear()

def test_openai_chat_completions_success(client, mock_orchestrator):
    """Verify standard OpenAI chat format is accepted and routed."""
    mock_orchestrator.process_query.return_value = "Mocked inventory intelligence response."
    
    payload = {
        "model": "gemini-pro",
        "messages": [
            {"role": "user", "content": "What is the stock of ITEM-123?"}
        ]
    }
    
    response = client.post("/v1/chat/completions", json=payload)
    
    # 1. API returns success and compatible JSON
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "gemini-pro"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "Mocked inventory intelligence response."
    
    # 2. User message reached the boundary
    mock_orchestrator.process_query.assert_called_once_with(
        query="What is the stock of ITEM-123?",
        id_urn="urn:aarambooks:intelligence:inventory",
        cem_urn="urn:aarambooks:cem:inventory",
        auth_context="open_webui_user"
    )

def test_openai_chat_completions_empty_messages(client, mock_orchestrator):
    """Verify validation of empty messages."""
    payload = {
        "model": "gemini-pro",
        "messages": []
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 400
    
def test_openai_chat_completions_orchestrator_error(client, mock_orchestrator):
    """Verify orchestrator errors are safely converted."""
    mock_orchestrator.process_query.side_effect = Exception("Internal domain error")
    
    payload = {
        "model": "gemini-pro",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 500
