"""
Pydantic schemas for the NDR Queue API — Brain-facing contracts.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class NDRClaimRequest(BaseModel):
    claimer_id: str = Field(..., description="Stable Brain instance identifier")
    lease_seconds: int = Field(600, ge=60, le=3600, description="Lease duration in seconds")


class NDRClaimResponse(BaseModel):
    queue_item_id: str
    awb_no: str
    ndr_attempt_seq: int
    ndr_time_at_enroll: Optional[datetime]
    ndr_reason_at_enroll: Optional[str]
    payment_mode: str
    current_engagement: Optional[Dict[str, Any]] = None
    ndr_context: Optional[Dict[str, Any]] = None  # NDRShipmentContext from existing API


class EngagementRegistrationRequest(BaseModel):
    queue_item_id: str = Field(..., description="From claim response")
    engagement_id: str = Field(..., description="Brain-assigned, e.g. eng_<uuid>")
    idempotency_key: str = Field(..., description="Brain-assigned, stable per registration attempt")


class EngagementRegistrationResponse(BaseModel):
    engagement_id: str
    status: str  # "created" | "existing"


class QueueStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="New queue status")
    engagement_id: Optional[str] = None
    call_sid: Optional[str] = None
    call_outcome: Optional[str] = None   # answered/no_answer/failed/cancelled
    transcript_id: Optional[str] = None
    transcript_summary: Optional[str] = None
    failure_class: Optional[str] = None
    failure_reason: Optional[str] = None


class QueueStatusUpdateResponse(BaseModel):
    queue_item_id: str
    queue_status: str
    will_retry: Optional[bool] = None


class NDRIntelligenceRequest(BaseModel):
    result_id: str = Field(..., description="Brain-assigned idempotency key")
    queue_item_id: str
    engagement_id: str
    awb_no: str
    recommended_action: str = Field(..., description="reschedule|accept_rto|escalate|no_action")
    diagnosis: Optional[str] = None
    customer_intent: Optional[str] = None  # agreed/declined/unreachable/unclear
    confidence_level: Optional[str] = None  # high/medium/low
    provenance: Optional[str] = None
    action_parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None
    risk_score: Optional[str] = None
    source_evidence: List[Any] = Field(default_factory=list)
    submitted_by: Optional[str] = None


class NDRIntelligenceResponse(BaseModel):
    status: str  # "persisted" | "duplicate"
    result_id: str


class ActionReadyItem(BaseModel):
    queue_item_id: str
    awb_no: str
    ndr_attempt_seq: int
    customer_name: Optional[str]
    ndr_reason_at_enroll: Optional[str]
    recommended_action: str
    action_parameters: Dict[str, Any]
    customer_intent: Optional[str]
    diagnosis: Optional[str]
    confidence_level: Optional[str]
    intelligence_at: Optional[datetime]
    engagement_id: Optional[str]
    action_ready_at: Optional[datetime]


class EnrollResponse(BaseModel):
    enrolled: int
    terminated: int
