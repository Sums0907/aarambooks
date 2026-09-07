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

    async def execute_engagement(
        self, 
        action_request: ActionRequest, 
        call_context: Optional[Dict[str, Any]] = None,
        ccc_snapshot: Optional[Dict[str, Any]] = None
    ) -> CustomerEngagementRecord:
        if not action_request.execution_intent:
            raise ValueError("CustomerEngagementExecutor requires an ActionRequest with an explicit execution_intent.")

        if call_context is None:
            # Fallback legacy behavior
            allowed_keys = ["awb_no", "customer_phone", "reattempt_date"]
            call_context = {
                key: action_request.parameters[key]
                for key in allowed_keys
                if key in action_request.parameters
            }

        # Create the initial engagement record (Status: REQUESTED) BEFORE calling adapter
        engagement = CustomerEngagementRecord(
            action_request_id=action_request.action_request_id,
            awb_no=action_request.parameters.get("awb_no", "UNKNOWN"),
            channel=action_request.execution_intent.channel.value,
            provider="EXOTEL" if action_request.execution_intent.channel == ExecutionChannel.VOICE else "UNKNOWN",
            call_context=call_context,
            ccc_snapshot=ccc_snapshot
        )
        
        await self.repository.create_engagement(engagement)
        
        # Route to provider adapter
        if engagement.provider == "EXOTEL" and self.exotel_adapter:
            try:
                # Dispatch the call via Exotel adapter
                dispatch_result = await self.exotel_adapter.dispatch_call(action_request, engagement.engagement_id)
                
                # Persist provider correlation IDs
                call_id = dispatch_result.get("call_id")
                await self.repository.update_engagement_correlation(
                    engagement.engagement_id,
                    call_id=call_id
                )
                
                # Transition to DISPATCHED
                await self.repository.transition_state(engagement.engagement_id, EngagementState.DISPATCHED)
                engagement.status = EngagementState.DISPATCHED
                engagement.provider_call_id = call_id
                
            except Exception as e:
                logger.error(f"Failed to dispatch Exotel call: {e}")
                await self.repository.transition_state(engagement.engagement_id, EngagementState.FAILED)
                engagement.status = EngagementState.FAILED
        else:
            await self.repository.transition_state(engagement.engagement_id, EngagementState.FAILED)
            engagement.status = EngagementState.FAILED
            
        return engagement
