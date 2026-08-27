import pytest
import os
from unittest.mock import patch, MagicMock
from src.brain_core.gateway.interfaces import GatewayGenerationRequest, GatewayMessage
from src.infrastructure.adapters.litellm_gateway import LiteLLMGatewayAdapter

@pytest.fixture
def adapter():
    return LiteLLMGatewayAdapter(
        base_url="http://localhost:4000",
        api_key="test_key",
        model="gemini-3.6-flash"
    )

@pytest.mark.asyncio
async def test_gateway_success_response(adapter):
    request = GatewayGenerationRequest(
        messages=[GatewayMessage(role="user", content="Hello")]
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hi there"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "gemini-3.6-flash"
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = await adapter.generate(request)
        
        assert response.content == "Hi there"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 5
        assert response.model_used == "gemini-3.6-flash"

@pytest.mark.asyncio
async def test_gateway_handles_empty_response(adapter):
    request = GatewayGenerationRequest(
        messages=[GatewayMessage(role="user", content="Test")]
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Simulate the length finish reason where content is None or empty choices
    mock_response.json.return_value = {
        "choices": [{"message": {"content": None}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 0},
        "model": "gemini-3.6-flash"
    }
    
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        response = await adapter.generate(request)
        
        assert response.content == ""
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 0
