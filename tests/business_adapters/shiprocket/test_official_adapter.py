import pytest
import json
import os
from typing import Optional, Dict, Any

from src.business_adapters.shiprocket.acquisition_client import ShiprocketAcquisitionClient
from src.business_adapters.shiprocket.adapter import ShiprocketAdapter
from src.shared.context_contracts.source import SourceSystem

class MockOfficialShiprocketClient(ShiprocketAcquisitionClient):
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        
    async def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        # Mocking the client which unwraps 'data' already:
        order = self.data.get("orders", {}).get(order_id)
        if order:
            return order.get("data")
        return None
        
    async def get_shipment_tracking(self, awb_no: str) -> Optional[Dict[str, Any]]:
        # Mocking the client which unwraps 'tracking_data' already:
        tracking = self.data.get("trackings", {}).get(awb_no)
        if tracking:
            return tracking.get("tracking_data")
        return None

@pytest.fixture
def official_shiprocket_data():
    filepath = os.path.join(os.path.dirname(__file__), "../../../sample-data/shiprocket/official_contract_fixture.json")
    with open(filepath, "r") as f:
        return json.load(f)

@pytest.fixture
def shiprocket_adapter(official_shiprocket_data):
    client = MockOfficialShiprocketClient(official_shiprocket_data)
    return ShiprocketAdapter(client)

@pytest.mark.asyncio
async def test_get_order_context(shiprocket_adapter):
    order_context = await shiprocket_adapter.get_order_context("SR_ORDER_999")
    
    assert order_context is not None
    assert order_context.order_reference == "SR_ORDER_999"
    assert order_context.source_system == SourceSystem.shiprocket
    assert order_context.status == "SHIPPED"
    
    assert len(order_context.items) == 1
    item = order_context.items[0]
    
    assert item["sku_id"] == "SKU_123"
    assert item["quantity"] == 1
    assert item["selling_price"] == 250.0

@pytest.mark.asyncio
async def test_get_customer_context(shiprocket_adapter):
    # Pass order ID as customer_reference because Shiprocket embeds customer in order
    customer_context = await shiprocket_adapter.get_customer_context("SR_ORDER_999")
    
    assert customer_context is not None
    assert customer_context.customer_reference is None
    assert customer_context.source_system == SourceSystem.shiprocket
    assert customer_context.name == "Official Customer"
    assert customer_context.phone_number == "9876543210"

@pytest.mark.asyncio
async def test_get_fulfillment_context(shiprocket_adapter):
    fulfillment_context = await shiprocket_adapter.get_fulfillment_context("SR_ORDER_999")
    
    assert fulfillment_context is not None
    assert fulfillment_context.fulfillment_status == "SHIPPED"

@pytest.mark.asyncio
async def test_get_shipment_context(shiprocket_adapter):
    shipment_context = await shiprocket_adapter.get_shipment_context("AWB_777")
    
    assert shipment_context is not None
    assert shipment_context.shipment_reference == "AWB_777"
    assert shipment_context.source_system == SourceSystem.shiprocket
    assert shipment_context.awb_no == "AWB_777"
    assert shipment_context.courier == "Delhivery"
    assert shipment_context.status == "NDR Raised"
    
    # Check delivery attempts logic (sr-status 17 and 19 are attempts, 18 is not inferred as attempt natively, or is it?
    # Our code checks `sr_status in [17, 19]`. 
    # In official_contract_fixture, we have:
    # sr-status 17 (OUT FOR DELIVERY)
    # sr-status 18 (UNDELIVERED)
    # The adapter will infer 17 as an attempt and add it to delivery_attempts.
    # It will NOT infer 18 as an attempt directly, keeping it in raw_tracking_events.
    
    assert len(shipment_context.delivery_attempts) == 1
    attempt = shipment_context.delivery_attempts[0]
    
    assert attempt.status == "SHIPMENT OUTSCAN" # from activity string
    assert attempt.remarks == "SOLAPUR" # location mapped to remarks
    
    # Check that 18 was preserved in raw_tracking_events
    assert len(shipment_context.raw_tracking_events) == 1
    preserved_event = shipment_context.raw_tracking_events[0]
    assert preserved_event["sr-status"] == 18
    assert preserved_event["activity"] == "NDR Raised - Customer Not Available"
