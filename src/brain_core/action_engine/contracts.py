from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Dict, Any, Optional

class ActionCategory(str, Enum):
    """Derived from docs/04-data-models/action-model.md Categories"""
    RECOMMENDATION = "recommendation"
    SUGGESTED_RESOLUTION = "suggested_resolution"
    AUTOMATED_RESPONSE = "automated_response"
    HUMAN_ASSISTANCE = "human_assistance"

class ActionRequest(BaseModel):
    """Represents a request for an intelligent action."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    category: ActionCategory
    reasoning: str
    parameters: Dict[str, Any]

class ActionResponse(BaseModel):
    """Represents the outcome of an action execution."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    success: bool
    message: str
    execution_result: Optional[Dict[str, Any]] = None
