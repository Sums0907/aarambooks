import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.business_adapters.inventory.adapter import AaramInventoryAdapter
from src.brain_core.models.contexts import InventoryContext

@pytest.fixture
def adapter():
    return AaramInventoryAdapter(
        base_url="http://inventory.local",
        identity_url="http://identity.local",
        client_id="test_client",
        client_secret="test_secret"
    )

@pytest.mark.asyncio
async def test_adapter_success_positive_balance(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "mock_token"}
        
        warehouse_response = MagicMock()
        warehouse_response.json.return_value = {"data": [{"id": "wh-123"}]}
        
        balance_response = MagicMock()
        balance_response.json.return_value = {
            "warehouse_id": "wh-123", 
            "sku_id": "sku-456", 
            "balance": 10,
            "confidence_score": 99.9 
        }
        
        mock_client.post.return_value = token_response
        mock_client.get.side_effect = [warehouse_response, balance_response]
        
        context = await adapter.get_inventory_context(["sku-456"])
        
        # Verify it's a normal instance
        assert isinstance(context, InventoryContext)
        
        # 1. SKU ID is passed correctly
        balance_call = mock_client.get.call_args_list[1]
        assert balance_call.kwargs["params"]["sku_id"] == "sku-456"
        
        # 2. Warehouse lookup occurs
        warehouse_call = mock_client.get.call_args_list[0]
        assert "masters/warehouses" in warehouse_call.args[0]
        
        # 6. Correct balance endpoint is called
        assert "read/inventory/balance" in balance_call.args[0]
        
        # 7. Correct warehouse_id is passed
        assert balance_call.kwargs["params"]["warehouse_id"] == "wh-123"
        
        # 9. Bearer Authorization header is present
        assert warehouse_call.kwargs["headers"] == {"Authorization": "Bearer mock_token"}
        assert balance_call.kwargs["headers"] == {"Authorization": "Bearer mock_token"}
        
        # 10. Positive balance maps to quantity_on_hand
        assert context.item_id == "sku-456"
        assert context.quantity_on_hand == 10.0
        
        # 12. confidence_score is completely ignored
        assert not hasattr(context, 'confidence_score')

@pytest.mark.asyncio
async def test_adapter_success_zero_balance(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "mock_token"}
        
        warehouse_response = MagicMock()
        warehouse_response.json.return_value = {"data": [{"id": "wh-123"}]}
        
        balance_response = MagicMock()
        balance_response.json.return_value = {"balance": 0}
        
        mock_client.post.return_value = token_response
        mock_client.get.side_effect = [warehouse_response, balance_response]
        
        context = await adapter.get_inventory_context(["sku-456"])
        
        assert isinstance(context, InventoryContext)
        # 11. Zero balance maps to quantity_on_hand
        assert context.quantity_on_hand == 0.0

@pytest.mark.asyncio
async def test_adapter_success_fractional_balance(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "mock_token"}
        
        warehouse_response = MagicMock()
        warehouse_response.json.return_value = {"data": [{"id": "wh-123"}]}
        
        balance_response = MagicMock()
        balance_response.json.return_value = {"balance": 15.5}
        
        mock_client.post.return_value = token_response
        mock_client.get.side_effect = [warehouse_response, balance_response]
        
        context = await adapter.get_inventory_context(["sku-456"])
        
        assert isinstance(context, InventoryContext)
        # Fractional balance is preserved
        assert context.quantity_on_hand == 15.5

@pytest.mark.asyncio
async def test_adapter_missing_balance_fails(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "mock_token"}
        
        warehouse_response = MagicMock()
        warehouse_response.json.return_value = {"data": [{"id": "wh-123"}]}
        
        balance_response = MagicMock()
        # Missing balance
        balance_response.json.return_value = {"warehouse_id": "wh-123"} 
        
        mock_client.post.return_value = token_response
        mock_client.get.side_effect = [warehouse_response, balance_response]
        
        with pytest.raises(ValueError, match="Balance field missing"):
            await adapter.get_inventory_context(["sku-456"])

@pytest.mark.asyncio
async def test_zero_warehouses_fails(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "mock_token"}
        
        warehouse_response = MagicMock()
        warehouse_response.json.return_value = {"data": []}
        
        mock_client.post.return_value = token_response
        mock_client.get.return_value = warehouse_response
        
        # 4. Zero warehouses fails
        with pytest.raises(ValueError, match="0 warehouses"):
            await adapter.get_inventory_context(["sku-456"])

@pytest.mark.asyncio
async def test_multiple_warehouses_fails(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "mock_token"}
        
        warehouse_response = MagicMock()
        warehouse_response.json.return_value = {"data": [{"id": "wh-1"}, {"id": "wh-2"}]}
        
        mock_client.post.return_value = token_response
        mock_client.get.return_value = warehouse_response
        
        # 5. Multiple warehouses fails
        with pytest.raises(ValueError, match="multi-warehouse"):
            await adapter.get_inventory_context(["sku-456"])

@pytest.mark.asyncio
async def test_http_failures_propagate(adapter):
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # 13. HTTP/network failures propagate
        mock_client.post.side_effect = httpx.RequestError("Network error")
        
        with pytest.raises(httpx.RequestError):
            await adapter.get_inventory_context(["sku-456"])
