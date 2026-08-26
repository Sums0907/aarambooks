import pytest
from pydantic import ValidationError
from src.brain_core.models.contexts import CustomerContext, OrderContext, ShipmentContext, InventoryContext

def test_customer_context_valid():
    ctx = CustomerContext(customer_id="cust-123")
    assert ctx.customer_id == "cust-123"
    assert ctx.interactions == []

def test_customer_context_frozen():
    ctx = CustomerContext(customer_id="cust-123")
    with pytest.raises(ValidationError):
        ctx.customer_id = "cust-456"

def test_customer_context_no_extra_fields():
    with pytest.raises(ValidationError):
        CustomerContext(customer_id="cust-123", hypothetical_field="value")

def test_order_context_valid():
    ctx = OrderContext(order_id="ord-123")
    assert ctx.order_id == "ord-123"

def test_order_context_frozen():
    ctx = OrderContext(order_id="ord-123")
    with pytest.raises(ValidationError):
        ctx.order_id = "ord-456"

def test_shipment_context_valid():
    ctx = ShipmentContext(shipment_id="ship-123")
    assert ctx.shipment_id == "ship-123"

def test_shipment_context_frozen():
    ctx = ShipmentContext(shipment_id="ship-123")
    with pytest.raises(ValidationError):
        ctx.shipment_id = "ship-456"

def test_inventory_context_valid():
    ctx = InventoryContext(item_id="item-123")
    assert ctx.item_id == "item-123"

def test_inventory_context_frozen():
    ctx = InventoryContext(item_id="item-123")
    with pytest.raises(ValidationError):
        ctx.item_id = "item-456"
