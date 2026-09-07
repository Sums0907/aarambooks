import uuid
from enum import Enum
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from src.intelligence_domains.ndr.contracts.action_request import OutreachChannel

class EngagementState(str, Enum):
    REQUESTED = "REQUESTED"
    DISPATCHED = "DISPATCHED"
    RINGING = "RINGING"
    CONNECTED = "CONNECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"

class ObservationalOutcome(str, Enum):
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    RESCHEDULE_REQUESTED = "RESCHEDULE_REQUESTED"
    REATTEMPT_ACCEPTED = "REATTEMPT_ACCEPTED"
    ADDRESS_CLARIFICATION = "ADDRESS_CLARIFICATION"
    CUSTOMER_REJECTED = "CUSTOMER_REJECTED"
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    UNKNOWN = "UNKNOWN"

class NormalizationStatus(str, Enum):
    NOT_READY = "NOT_READY"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRY_PENDING = "RETRY_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class CustomerEngagementRecord(BaseModel):
    engagement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_request_id: str
    ndr_id: Optional[str] = None
    awb_no: str
    channel: OutreachChannel
    provider: str
    provider_session_id: Optional[str] = None
    provider_call_id: Optional[str] = None
    provider_conversation_id: Optional[str] = None
    status: EngagementState = EngagementState.REQUESTED
    normalization_status: str = NormalizationStatus.NOT_READY
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    raw_observational_outcome: Optional[str] = None
    normalized_outcome: Optional[ObservationalOutcome] = None
    call_context: Dict[str, Any] = Field(default_factory=dict)
    ccc_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class CustomerEngagementEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: Optional[str] = None
    provider: str
    provider_session_id: Optional[str] = None
    sequence: int = 0
    event_type: str
    provider_event_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
