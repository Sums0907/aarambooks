import pytest
from unittest.mock import patch, MagicMock
import httpx
from src.business_adapters.shiprocket.live_client import LiveShiprocketClient

@pytest.fixture
def client():
    return LiveShiprocketClient(email="test@example.com", password="pass")

def _mock_response(status_code, json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
@patch("httpx.AsyncClient.post")
async def test_authentication_and_caching(mock_post, mock_request, client):
    mock_post.return_value = _mock_response(200, {"token": "test-token-123"})
    mock_request.return_value = _mock_response(200, {"data": {"id": 123}})
    
    # First request should trigger auth
    data = await client.get_order_details("123")
    assert mock_post.called
    assert mock_post.call_count == 1
    assert data["id"] == 123
    
    # Second request should use cached token
    data2 = await client.get_order_details("123")
    assert mock_post.call_count == 1  # Still 1, token was cached
    assert data2["id"] == 123

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
@patch("httpx.AsyncClient.post")
async def test_401_reauthentication(mock_post, mock_request, client):
    mock_post.return_value = _mock_response(200, {"token": "new-token"})
    
    mock_request.side_effect = [
        _mock_response(401, {"message": "Unauthorized"}),
        _mock_response(200, {"data": {"id": 123}})
    ]
    
    # Force initial token
    client._token = "old-token"
    
    data = await client.get_order_details("123")
    
    # It should have called auth to get new-token
    assert mock_post.call_count == 1
    assert mock_request.call_count == 2
    assert data["id"] == 123
    assert client._token == "new-token"

@pytest.mark.asyncio
@patch("asyncio.sleep") # mock sleep to make test fast
@patch("httpx.AsyncClient.request")
@patch("httpx.AsyncClient.post")
async def test_429_retry_behaviour(mock_post, mock_request, mock_sleep, client):
    mock_post.return_value = _mock_response(200, {"token": "token"})
    
    mock_request.side_effect = [
        _mock_response(429, {"message": "Too Many Requests"}),
        _mock_response(429, {"message": "Too Many Requests"}),
        _mock_response(200, {"tracking_data": {"status": "ok"}})
    ]
    
    data = await client.get_shipment_tracking("AWB1")
    assert mock_request.call_count == 3
    assert data["status"] == "ok"
