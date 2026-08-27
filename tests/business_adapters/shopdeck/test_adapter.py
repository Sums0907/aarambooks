import pytest
import json
import os
from typing import Optional, Dict, Any, List

from src.business_adapters.shopdeck.acquisition_client import ShopDeckAcquisitionClient
from src.business_adapters.shopdeck.adapter import ShopDeckAdapter
from src.shared.context_contracts.source import SourceSystem

class MockShopDeckClient(ShopDeckAcquisitionClient):
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        
    async def get_order_summary(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.data.get("order_summary", {}).get(order_id)
        
    async def get_order_line_items(self, order_id: str) -> List[Dict[str, Any]]:
        return self.data.get("order_line_items", {}).get(order_id, [])
        
    async def get_customer_info(self, awb_no: str) -> Optional[Dict[str, Any]]:
        for c in self.data.get("customer_info", {}).values():
            if c.get("awb_no") == awb_no:
                return c
        return None

    async def get_customer_info_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        return self.data.get("customer_info", {}).get(customer_id)
        
    async def get_shipment_ndr_report(self, awb_no: str) -> Optional[Dict[str, Any]]:
        return None
        
    async def get_ndr_action_log(self, awb_no: str) -> List[Dict[str, Any]]:
        return []

@pytest.fixture
def shopdeck_data():
    filepath = os.path.join(os.path.dirname(__file__), "../../../sample-data/shopdeck/synthetic_schemas.json")
    with open(filepath, "r") as f:
        return json.load(f)

@pytest.fixture
def shopdeck_adapter(shopdeck_data):
    client = MockShopDeckClient(shopdeck_data)
    return ShopDeckAdapter(client)

@pytest.mark.asyncio
async def test_get_order_context(shopdeck_adapter):
    order_context = await shopdeck_adapter.get_order_context("123")
    
    assert order_context is not None
    assert order_context.order_reference == "123"
    assert order_context.source_system == SourceSystem.shopdeck
    assert order_context.status == "Pending"  # payment_status in fixture is false
    
    assert len(order_context.items) == 1
    item = order_context.items[0]
    
    # Assert missing sku_id is preserved exactly as None, NOT hallucinated
    assert item["sku_id"] is None
    assert item["awb_no"] == "AWB_1001"
    assert item["seller_last_status"] == "dispatched"

@pytest.mark.asyncio
async def test_get_customer_context(shopdeck_adapter):
    customer_context = await shopdeck_adapter.get_customer_context("C_555")
    
    assert customer_context is not None
    assert customer_context.customer_reference == "C_555"
    assert customer_context.source_system == SourceSystem.shopdeck
    assert customer_context.name == "Test User"
    
    # Phone number cannot be used natively
    assert customer_context.phone_number is None

@pytest.mark.asyncio
async def test_get_fulfillment_context(shopdeck_adapter):
    fulfillment_context = await shopdeck_adapter.get_fulfillment_context("123")
    
    assert fulfillment_context is not None
    assert fulfillment_context.fulfillment_status == "dispatched"

@pytest.mark.asyncio
async def test_get_order_context_not_found(shopdeck_adapter):
    order_context = await shopdeck_adapter.get_order_context("999_missing")
    assert order_context is None
