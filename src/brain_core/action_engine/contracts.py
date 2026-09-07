import uuid
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from typing import Dict, Any, Optional

class ActionCategory(str, Enum):
    """Derived from docs/04-data-models/action-model.md Categories"""
    RECOMMENDATION = "recommendation"
    SUGGESTED_RESOLUTION = "suggested_resolution"
    AUTOMATED_RESPONSE = "automated_response"
    HUMAN_ASSISTANCE = "human_assistance"

class ExecutionChannel(str, Enum):
    VOICE = "VOICE"

class ExecutionIntent(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    intent_type: str
    channel: ExecutionChannel

class ConversationalDirective(BaseModel):
    """Domain-agnostic public contract defining what a conversation should accomplish."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    objective: str
    context_summary: str
    allowed_actions: list[str]
    constraints: list[str]


class ActionRequest(BaseModel):
    """Represents a request for an intelligent action."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    action_request_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    category: ActionCategory
    reasoning: str
    parameters: Dict[str, Any]
    execution_intent: Optional[ExecutionIntent] = None
    directive: Optional[ConversationalDirective] = None

class ActionResponse(BaseModel):
    """Represents the outcome of an action execution."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    success: bool
    message: str
    execution_result: Optional[Dict[str, Any]] = None
