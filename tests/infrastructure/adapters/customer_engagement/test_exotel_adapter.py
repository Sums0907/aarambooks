import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from src.shared.config import settings
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ExecutionIntent, ExecutionChannel
from src.infrastructure.adapters.customer_engagement.exotel_adapter import ExotelVoiceBotAdapter

@pytest.fixture
def adapter():
    settings.exotel_api_key = "test_key"
    settings.exotel_api_token = "test_token"
    settings.exotel_subdomain = "api.exotel.com"
    settings.exotel_account_sid = "test_sid"
    settings.exotel_caller_id = "0111111111"
    settings.exotel_voicebot_flow_url = "http://flow.url"
    return ExotelVoiceBotAdapter()

def build_mock_action(phone="9876543210"):
    return ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test",
        parameters={"customer_phone": phone} if phone else {},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)
    )

@pytest.mark.asyncio
async def test_exotel_adapter_dispatch_success(adapter):
    action = build_mock_action()
    
    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"Call": {"Sid": "exotel_call_sid_123", "Status": "queued"}}
        mock_instance.post.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await adapter.dispatch_call(action, "eng_123")

        assert result["call_id"] == "exotel_call_sid_123"

@pytest.mark.asyncio
async def test_exotel_adapter_timeout_no_retry(adapter):
    action = build_mock_action()
    
    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = httpx.TimeoutException("Network timeout")
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(RuntimeError):
            await adapter.dispatch_call(action, "eng_123")
        
@pytest.mark.asyncio
async def test_exotel_adapter_429_no_retry(adapter):
    action = build_mock_action()
    
    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"
        error = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = error
        mock_instance.post.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(RuntimeError, match="429"):
            await adapter.dispatch_call(action, "eng_123")

@pytest.mark.asyncio
async def test_exotel_adapter_500_no_retry(adapter):
    action = build_mock_action()
    
    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        error = httpx.HTTPStatusError("500 Internal Server Error", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = error
        mock_instance.post.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(RuntimeError, match="500"):
            await adapter.dispatch_call(action, "eng_123")

@pytest.mark.asyncio
async def test_exotel_adapter_missing_context(adapter):
    action = build_mock_action(phone=None)

    with patch('src.infrastructure.adapters.customer_engagement.exotel_adapter.settings.test_phone_override', ""):
        with pytest.raises(ValueError, match="Customer phone number missing"):
            await adapter.dispatch_call(action, "eng-456")
