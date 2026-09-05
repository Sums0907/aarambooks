import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from src.infrastructure.adapters.customer_engagement.exotel_adapter import ExotelVoiceBotAdapter
from src.intelligence_domains.ndr.contracts.action_request import ActionRequest, ActionType, OutreachChannel
from src.shared.config import settings

@pytest.fixture
def setup_exotel_settings():
    settings.exotel_api_key = "test_key"
    settings.exotel_api_token = "test_token"
    settings.exotel_account_sid = "test_sid"
    settings.exotel_subdomain = "api.exotel.com"
    settings.exotel_caller_id = "01122334455"
    settings.exotel_voicebot_flow_url = "http://flow.exotel.com"
    settings.aaram_exotel_webhook_secret = "test_secret"

@pytest.mark.asyncio
async def test_exotel_adapter_dispatch_success(setup_exotel_settings):
    adapter = ExotelVoiceBotAdapter()
    request = ActionRequest(
        action_request_id="req-123",
        awb_no="AWB123",
        action_type=ActionType.CUSTOMER_NDR_OUTREACH,
        channel=OutreachChannel.VOICE,
        objective="TEST",
        context={"customer_phone": "9876543210"}
    )

    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"Call": {"Sid": "mock_exotel_sid", "Status": "queued"}}
        mock_instance.post.return_value = mock_resp
        
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await adapter.dispatch_call(request, "eng-456")

        assert result["call_id"] == "mock_exotel_sid"
        assert result["status"] == "queued"

        mock_instance.post.assert_called_once()
        args, kwargs = mock_instance.post.call_args
        assert "eng-456|req-123|" in kwargs['data']['CustomField']

@pytest.mark.asyncio
async def test_exotel_adapter_timeout_no_retry(setup_exotel_settings):
    adapter = ExotelVoiceBotAdapter()
    request = ActionRequest(
        action_request_id="req-123", awb_no="AWB123", action_type=ActionType.CUSTOMER_NDR_OUTREACH,
        channel=OutreachChannel.VOICE, objective="TEST", context={"customer_phone": "9876543210"}
    )

    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = httpx.TimeoutException("Connection timeout")
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(RuntimeError, match="Exotel timeout"):
            await adapter.dispatch_call(request, "eng-456")
            
        mock_instance.post.assert_called_once() # PROVES NO RETRY

@pytest.mark.asyncio
async def test_exotel_adapter_429_no_retry(setup_exotel_settings):
    adapter = ExotelVoiceBotAdapter()
    request = ActionRequest(
        action_request_id="req-123", awb_no="AWB123", action_type=ActionType.CUSTOMER_NDR_OUTREACH,
        channel=OutreachChannel.VOICE, objective="TEST", context={"customer_phone": "9876543210"}
    )

    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"
        # Since we use raise_for_status(), we need to simulate raising HTTPStatusError
        error = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = error
        mock_instance.post.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(RuntimeError, match="Exotel HTTP 429"):
            await adapter.dispatch_call(request, "eng-456")
            
        mock_instance.post.assert_called_once()

@pytest.mark.asyncio
async def test_exotel_adapter_500_no_retry(setup_exotel_settings):
    adapter = ExotelVoiceBotAdapter()
    request = ActionRequest(
        action_request_id="req-123", awb_no="AWB123", action_type=ActionType.CUSTOMER_NDR_OUTREACH,
        channel=OutreachChannel.VOICE, objective="TEST", context={"customer_phone": "9876543210"}
    )

    with patch("src.infrastructure.adapters.customer_engagement.exotel_adapter.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_resp.text = "Bad Gateway"
        error = httpx.HTTPStatusError("502 Bad Gateway", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = error
        mock_instance.post.return_value = mock_resp
        mock_client.return_value.__aenter__.return_value = mock_instance

        with pytest.raises(RuntimeError, match="Exotel HTTP 502"):
            await adapter.dispatch_call(request, "eng-456")
            
        mock_instance.post.assert_called_once()

@pytest.mark.asyncio
async def test_exotel_adapter_missing_context(setup_exotel_settings):
    adapter = ExotelVoiceBotAdapter()
    request = ActionRequest(
        action_request_id="req-123",
        awb_no="AWB123",
        action_type=ActionType.CUSTOMER_NDR_OUTREACH,
        channel=OutreachChannel.VOICE,
        objective="TEST",
        context={}  # Missing phone number
    )

    with pytest.raises(ValueError, match="Customer phone number missing"):
        await adapter.dispatch_call(request, "eng-456")
