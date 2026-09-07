from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class OrderLineItem(BaseModel):
    """Business representation of a single product inside a shipment."""
    sku_id: Optional[str] = Field(None, description="SKU ID of the product")
    product_code: Optional[str] = Field(None, description="Product code/ID")
    product_name: Optional[str] = Field(None, description="Name of the product")
    quantity: int = Field(0, description="Quantity ordered")
    selling_price: float = Field(0.0, description="Price per unit")


class NDRActionHistory(BaseModel):
    """Business representation of a single action taken to resolve an NDR."""
    action_type: str = Field(..., description="Type of action taken (e.g. ivr_call, whatsapp_hsm, seller_reattempt, dispute)")
    action_by: str = Field(..., description="Initiator of the action (e.g. AI_AGENT, SYSTEM, SUPPORT_AGENT)")
    action_time: Optional[datetime] = Field(None, description="When the action was performed")
    response_status: Optional[str] = Field(None, description="Customer or carrier response status")
    response_time: Optional[datetime] = Field(None, description="When the response was received")
    remarks: Optional[str] = Field(None, description="Notes or customer feedback details")
    message_text: Optional[str] = Field(None, description="Content of the message sent")
    reattempt_date: Optional[datetime] = Field(None, description="Reattempt date committed by customer/seller")
    is_priority_escalate: bool = Field(False, description="Whether this case was escalated to human support")
    call_duration: Optional[str] = Field(None, description="Duration of voice call if applicable")

class NDRShipmentContext(BaseModel):
    """Canonical business representation of a shipment experiencing a delivery exception (NDR)."""
    awb_no: str = Field(..., description="Air Waybill tracking number")
    order_id: Optional[str] = Field(None, description="Unique Order ID")
    order_date: Optional[datetime] = Field(None, description="Timestamp when the order was placed")
    order_status: str = Field(..., description="Current status of the shipment")
    courier_partner: str = Field(..., description="Name of the 3PL courier partner")
    customer_id: str = Field(..., description="Customer unique identifier")
    customer_name: Optional[str] = Field(None, description="Recipient customer name")
    customer_number: Optional[str] = Field(None, description="Customer phone number from customer_info — authoritative contact for outreach")
    payment_mode: str = Field(..., description="Payment mode (cod, prepaid)")
    pickup_time: Optional[datetime] = Field(None, description="Time the parcel was picked up from warehouse")
    latest_ndr_time: Optional[datetime] = Field(None, description="Timestamp of the most recent delivery failure scan")
    latest_ndr_reason: Optional[str] = Field(None, description="Reason text recorded for the latest NDR")
    latest_ofd_time: Optional[datetime] = Field(None, description="Timestamp when the parcel was last marked Out For Delivery")
    delivery_time: Optional[datetime] = Field(None, description="Timestamp of successful delivery if recovered")
    ndr_count: int = Field(0, description="Total number of failed delivery attempts so far")
    ofd_count: int = Field(0, description="Total number of times marked Out For Delivery")
    seller_actions: Optional[str] = Field(None, description="Actions recorded by the seller or system")
    ndr_status: str = Field(..., description="High-level NDR state")
    
    # Aggregated business context
    cod_amount: float = Field(0.0, description="Total amount to be collected on delivery")
    items: List[OrderLineItem] = Field(default_factory=list, description="List of products in this shipment")
    action_history: List[NDRActionHistory] = Field(default_factory=list, description="Chronological log of resolution actions taken")

class IntelligenceResult(BaseModel):
    """Canonical NDR Intelligence Result contract for Mock ShopDeck BS persistence."""
    normalization_id: str
    brain_decision_id: Optional[str] = None
    target_identity: str
    recommendation: Optional[str] = None
    authorized_action: str
    action_parameters: dict = Field(default_factory=dict)
    reasoning: Optional[str] = None
    diagnosis: Optional[str] = None
    risk_score: Optional[str] = None
    source_event_ids: List[str] = Field(default_factory=list)
    provenance: Optional[str] = None
    normalization_status: Optional[str] = None
