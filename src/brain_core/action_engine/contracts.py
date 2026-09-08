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

class ConversationMissionContract(BaseModel):
    """
    Domain-agnostic contract describing WHY an outbound conversation exists and what
    "done" looks like, so the execution layer cannot drift away from the objective.

    Deliberately NOT a state machine. This is a call-scoped, immutable snapshot carried
    into the voice session alongside authoritative business facts.

    `initial_state` is the state the conversation OPENS in. It is named `initial_` and not
    `current_` on purpose: this object is frozen and embedded in an immutable CCC snapshot,
    so it cannot represent a state that advances during the call. V1 has no server-side
    per-turn transition engine; `allowed_next_states` is prompt-level guidance to the
    conversational layer, not an enforced transition table.

    State VALUES are owned by the domain (e.g. src/intelligence_domains/ndr defines the
    NDR state vocabulary). This contract stays domain-agnostic in shape.
    """
    model_config = ConfigDict(frozen=True, extra='forbid')

    conversation_mission: str
    why_this_call: str
    primary_objective: str
    success_condition: str
    initial_state: str
    allowed_actions: list[str]
    allowed_next_states: list[str]
    conversation_priority: str
    return_to_mission: str


class ConversationalDirective(BaseModel):
    """Domain-agnostic public contract defining what a conversation should accomplish."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    objective: str
    context_summary: str
    allowed_actions: list[str]
    constraints: list[str]
    mission: Optional[ConversationMissionContract] = None

    @property
    def effective_allowed_actions(self) -> list[str]:
        """
        Single authority for permitted actions.

        `allowed_actions` exists on both this directive and on the mission. The mission wins
        whenever one is attached, so exactly one list ever reaches the conversational layer
        and there is no ambiguity about which is binding.
        """
        if self.mission is not None:
            return self.mission.allowed_actions
        return self.allowed_actions


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
