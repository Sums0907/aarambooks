from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from src.shared.context_contracts.source import SourceSystem, ContextSource

class DeliveryAttempt(BaseModel):
    attempt_timestamp: datetime
    status: str
    reason: Optional[str] = None
    remarks: Optional[str] = None

class ShipmentContext(BaseModel):
    shipment_reference: str
    source_system: SourceSystem
    awb_no: str
    courier: str
    status: str
    delivery_attempts: List[DeliveryAttempt] = Field(default_factory=list)
    raw_tracking_events: List[dict] = Field(default_factory=list)
    source: ContextSource
