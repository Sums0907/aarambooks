from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
import uuid

from src.shared.evidence_request_contracts import AbstractEvidenceRequest

class DecisionStatus(str, Enum):
    PROCEED = "PROCEED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"

class ConfirmationRequired(BaseModel):
    nonce: str
    original_request: AbstractEvidenceRequest
    structured_data: Optional[Dict[str, Any]] = None # For R-8 rendering

class Recommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proposed_request: AbstractEvidenceRequest
    structured_data: Optional[Dict[str, Any]] = None # For R-8 rendering
    nonce: Optional[str] = None # Filled when the recommendation is suspended as a pending action

class DecisionResponse(BaseModel):
    status: DecisionStatus
    confirmation_context: Optional[ConfirmationRequired] = None
    recommendations: List[Recommendation] = Field(default_factory=list)
