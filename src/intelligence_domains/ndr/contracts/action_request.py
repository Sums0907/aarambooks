from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    CUSTOMER_NDR_OUTREACH = "CUSTOMER_NDR_OUTREACH"
    # Other actions can be added here (e.g. COURIER_DISPUTE)

class OutreachChannel(str, Enum):
    VOICE = "VOICE"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"

class AllowedOutcome(str, Enum):
    RESCHEDULE = "RESCHEDULE"
    REATTEMPT = "REATTEMPT"
    ADDRESS_CLARIFICATION = "ADDRESS_CLARIFICATION"
    CANCEL = "CANCEL"
    CUSTOMER_REJECTS = "CUSTOMER_REJECTS"

class ActionRequest(BaseModel):
    action_request_id: str
    awb_no: str
    action_type: ActionType
    channel: OutreachChannel
    objective: str
    language: str = "HINGLISH"
    allowed_outcomes: List[AllowedOutcome] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict, description="Pre-authorized bounded context for engagement")
    
    # We do NOT include Exotel specific types here.
