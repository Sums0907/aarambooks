from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.conversational_contracts import ConversationalResponse

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SuspendedActionStatus(str, Enum):
    PENDING = "PENDING"
    CONSUMED = "CONSUMED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class ConversationSession(BaseModel):
    model_config = ConfigDict(frozen=True)
    tenant_id: str
    client_id: str
    user_id: str
    session_id: str
    created_at: datetime = Field(default_factory=utc_now)

class ConversationTurn(BaseModel):
    model_config = ConfigDict(frozen=True)
    turn_id: str
    session_id: str
    user_utterance: str
    system_response: ConversationalResponse
    timestamp: datetime = Field(default_factory=utc_now)

class SuspendedExecutionState(BaseModel):
    model_config = ConfigDict(frozen=True)
    nonce: str
    session_id: str
    request: AbstractEvidenceRequest
    status: SuspendedActionStatus = SuspendedActionStatus.PENDING
    expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
