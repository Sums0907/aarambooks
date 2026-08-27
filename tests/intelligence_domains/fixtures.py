from datetime import datetime
from src.brain_core.models.contexts import CustomerContext, OrderContext, ShipmentContext, DeliveryAttempt

# --- Normal Order Status Query ---
normal_order = OrderContext(order_id="ORD-001")
normal_customer = CustomerContext(
    customer_id="CUST-001",
    interactions=["Asked about book release"],
    needs=["Standard delivery"],
    previous_conversations=[],
    resolution_history=[],
    relevant_business_situations=[]
)

# --- NDR / Customer Not Available ---
ndr_shipment = ShipmentContext(
    shipment_id="SHIP-001",
    awb_no="AWB-12345",
    courier="Shiprocket",
    status="Failed",
    delivery_attempts=[
        DeliveryAttempt(attempt_timestamp=datetime(2026, 8, 25, 14, 0), status="Failed", reason="Customer Not Available")
    ]
)

# --- High-Value Dispute / Escalation ---
high_value_order = OrderContext(order_id="ORD-999")
escalation_customer = CustomerContext(
    customer_id="CUST-VIP",
    interactions=[],
    needs=[],
    previous_conversations=["Customer was extremely angry yesterday."],
    resolution_history=[],
    relevant_business_situations=["High churn risk"]
)

# --- Missing Context ---
missing_order = None # Deliberately missing

