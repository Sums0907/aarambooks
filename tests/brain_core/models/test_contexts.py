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
    shipment = ShipmentContext(
        shipment_id="shp-123",
        awb_no="AWB_TEST",
        courier="Delhivery",
        status="Shipped",
        delivery_attempts=[]
    )
    assert shipment.shipment_id == "shp-123"
    assert shipment.awb_no == "AWB_TEST"

def test_shipment_context_frozen():
    shipment = ShipmentContext(
        shipment_id="shp-123",
        awb_no="AWB_TEST",
        courier="Delhivery",
        status="Shipped",
        delivery_attempts=[]
    )
    with pytest.raises(ValidationError):
        shipment.shipment_id = "ship-456"

def test_inventory_context_valid():
    # 1. InventoryContext(item_id="x") remains valid.
    # 2. Missing quantity_on_hand defaults to 0.0.
    ctx = InventoryContext(item_id="item-123")
    assert ctx.item_id == "item-123"
    assert ctx.quantity_on_hand == 0.0

def test_inventory_context_explicit_and_fractional():
    # 3. Explicit quantity_on_hand values are preserved.
    # 4. Fractional values are supported.
    ctx = InventoryContext(item_id="item-123", quantity_on_hand=15.5)
    assert ctx.item_id == "item-123"
    assert ctx.quantity_on_hand == 15.5

def test_inventory_context_frozen():
    # 5. The model remains frozen.
    ctx = InventoryContext(item_id="item-123")
    with pytest.raises(ValidationError):
        ctx.item_id = "item-456"
    with pytest.raises(ValidationError):
        ctx.quantity_on_hand = 10.0

def test_inventory_context_no_extra_fields():
    # 6. Unknown extra fields remain rejected.
    # 8. No confidence_score exists on InventoryContext.
    with pytest.raises(ValidationError) as exc:
        InventoryContext(item_id="item-123", confidence_score=99)
    assert "confidence_score" in str(exc.value)

    with pytest.raises(ValidationError):
        InventoryContext(item_id="item-123", hypothetical_field="value")

def test_inventory_context_schema():
    # 7. quantity_on_hand is part of the declared Pydantic model/schema.
    schema = InventoryContext.model_json_schema()
    assert "quantity_on_hand" in schema["properties"]
    assert schema["properties"]["quantity_on_hand"]["type"] == "number"
