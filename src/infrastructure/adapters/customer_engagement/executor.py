import uuid
from enum import Enum
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.brain_core.action_engine.contracts import ActionRequest, ExecutionChannel
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository, NormalizationStatus

logger = logging.getLogger(__name__)

from src.infrastructure.adapters.customer_engagement.models import (
    CustomerEngagementRecord,
    CustomerEngagementEvent,
    EngagementState,
    ObservationalOutcome
)

class CustomerEngagementExecutor:
    """
    Generic Customer Engagement Execution Boundary.
    Resolves ActionRequest to engagement config and routes to the provider adapter.
    """
    def __init__(self, repository: CustomerEngagementRepository, exotel_adapter=None):
        self.repository = repository
        self.exotel_adapter = exotel_adapter

    async def prepare_engagement(
        self,
        action_request: ActionRequest,
        engagement_id: str,
        call_context: Optional[Dict[str, Any]] = None,
        ccc_snapshot: Optional[Dict[str, Any]] = None
    ) -> CustomerEngagementRecord:
        if not action_request.execution_intent:
            raise ValueError("CustomerEngagementExecutor requires an ActionRequest with an explicit execution_intent.")

        if call_context is None:
            allowed_keys = ["awb_no", "customer_phone", "reattempt_date"]
            call_context = {
                key: action_request.parameters[key]
                for key in allowed_keys
                if key in action_request.parameters
            }

        engagement = CustomerEngagementRecord(
            engagement_id=engagement_id,
            action_request_id=action_request.action_request_id,
            awb_no=action_request.parameters.get("awb_no", "UNKNOWN"),
            channel=action_request.execution_intent.channel.value,
            provider="EXOTEL" if action_request.execution_intent.channel == ExecutionChannel.VOICE else "UNKNOWN",
            call_context=call_context,
            ccc_snapshot=ccc_snapshot
        )
        
        # We rely on the repository to handle Idempotency via DuplicateKeyError
        await self.repository.create_engagement(engagement)
        return engagement

    async def dispatch_provider_call(self, engagement: CustomerEngagementRecord, action_request: ActionRequest) -> Dict[str, Any]:
        if engagement.provider == "EXOTEL" and self.exotel_adapter:
            return await self.exotel_adapter.dispatch_call(action_request, engagement.engagement_id)
        raise ValueError(f"No suitable provider adapter for {engagement.provider}")

    async def persist_provider_correlation(self, engagement_id: str, provider_interaction_id: str) -> None:
        await self.repository.update_engagement_correlation(
            engagement_id,
            call_id=provider_interaction_id
        )
        await self.repository.transition_state(engagement_id, EngagementState.DISPATCHED)

    async def fail_engagement(self, engagement_id: str, reason: str = "") -> None:
        await self.repository.transition_state(engagement_id, EngagementState.FAILED)

    async def execute_engagement(
        self, 
        action_request: ActionRequest, 
        call_context: Optional[Dict[str, Any]] = None,
        ccc_snapshot: Optional[Dict[str, Any]] = None
    ) -> CustomerEngagementRecord:
        engagement_id = f"eng_{uuid.uuid4().hex}"
        engagement = await self.prepare_engagement(action_request, engagement_id, call_context, ccc_snapshot)
        
        try:
            dispatch_result = await self.dispatch_provider_call(engagement, action_request)
            call_id = dispatch_result.get("call_id")
            await self.persist_provider_correlation(engagement.engagement_id, call_id)
            engagement.status = EngagementState.DISPATCHED
            engagement.provider_call_id = call_id
        except Exception as e:
            logger.error(f"Failed to dispatch call: {e}")
            await self.fail_engagement(engagement.engagement_id, str(e))
            engagement.status = EngagementState.FAILED
            
        return engagement
