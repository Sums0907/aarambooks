import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta

from src.shared.evidence_request_contracts import AbstractEvidenceRequest
from src.shared.decision_contracts import DecisionResponse, DecisionStatus, ConfirmationRequired, Recommendation
from src.brain_core.memory.interfaces import MemoryProvider
from src.shared.memory_contracts import SuspendedExecutionState, SuspendedActionStatus
from src.shared.conversational_contracts import ConversationalIntent

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class DecisionEngine:
    def __init__(self, memory_provider: MemoryProvider):
        self._memory_provider = memory_provider

    async def evaluate_request(
        self,
        request: AbstractEvidenceRequest,
        session_id: str,
        ttl_seconds: int = 300
    ) -> DecisionResponse:
        """
        Determines whether a structurally valid AbstractEvidenceRequest requires confirmation.
        """
        intent = request.classified_requirement.understanding.intent
        
        if intent != ConversationalIntent.ACTION:
            return DecisionResponse(status=DecisionStatus.PROCEED)
            
        nonce = str(uuid.uuid4())
        state = SuspendedExecutionState(
            nonce=nonce,
            session_id=session_id,
            request=request,
            status=SuspendedActionStatus.PENDING,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds)
        )
        
        await self._memory_provider.suspend_action(state, ttl_seconds)
        
        return DecisionResponse(
            status=DecisionStatus.CONFIRMATION_REQUIRED,
            confirmation_context=ConfirmationRequired(
                nonce=nonce,
                original_request=request
            )
        )

    async def process_intent(
        self,
        intent: ConversationalIntent,
        session_id: str,
        nonce: str
    ) -> DecisionResponse:
        """
        Processes an explicit CONFIRMATION or REJECTION intent.
        Returns PROCEED for unrelated turns, leaving pending action untouched.
        """
        if intent not in (ConversationalIntent.CONFIRMATION, ConversationalIntent.REJECTION):
            # Unrelated query leaves pending action intact
            return DecisionResponse(status=DecisionStatus.PROCEED)

        state = await self._memory_provider.retrieve_suspended_action(nonce, session_id)
        if not state:
            return DecisionResponse(status=DecisionStatus.REJECTED)

        if intent == ConversationalIntent.CONFIRMATION:
            success = await self._memory_provider.atomic_consume_action(nonce, session_id)
            if success:
                return DecisionResponse(
                    status=DecisionStatus.CONFIRMED,
                    confirmation_context=ConfirmationRequired(
                        nonce=nonce,
                        original_request=state.request
                    )
                )
            else:
                return DecisionResponse(status=DecisionStatus.REJECTED)
                
        elif intent == ConversationalIntent.REJECTION:
            # We atomically consume it to effectively mark it as rejected (no longer PENDING)
            # using the existing interface capabilities.
            await self._memory_provider.atomic_consume_action(nonce, session_id)
            return DecisionResponse(status=DecisionStatus.REJECTED)

    async def evaluate_evidence_for_recommendations(
        self,
        response: 'BusinessEvidenceResponse',
        original_request: AbstractEvidenceRequest,
        session_id: str,
        ttl_seconds: int = 300
    ) -> DecisionResponse:
        """
        Evaluates a successful evidence response to proactively suggest actions without autonomy.
        """
        # Start with a PROCEED state since the original query succeeded
        decision = DecisionResponse(status=DecisionStatus.PROCEED)
        
        # We only generate recommendations for non-mutative requests
        if original_request.classified_requirement.understanding.intent == ConversationalIntent.ACTION:
            return decision

        # Extract data robustly (accounting for legacy adapter `evidence` vs `evidence_data`)
        data = getattr(response, "evidence_data", None)
        if data is None and hasattr(response, "evidence"):
            data = getattr(response, "evidence", None)
            
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items", [data])
            
        for item in items:
            if isinstance(item, dict) and item.get("open_exceptions", 0) > 0:
                # Deterministic rule: If there are open exceptions, recommend resolving them.
                # Propagate entities (e.g., the SKU) from the original request.
                entities = original_request.classified_requirement.understanding.entities
                
                proposed = AbstractEvidenceRequest(
                    classified_requirement=original_request.classified_requirement.__class__(
                        understanding=original_request.classified_requirement.understanding.__class__(
                            original_query="Resolve open exceptions",
                            intent=ConversationalIntent.ACTION,
                            entities=entities
                        ),
                        components=[]
                    )
                )
                
                nonce = str(uuid.uuid4())
                state = SuspendedExecutionState(
                    nonce=nonce,
                    session_id=session_id,
                    request=proposed,
                    status=SuspendedActionStatus.PENDING,
                    expires_at=utc_now() + timedelta(seconds=ttl_seconds)
                )
                
                await self._memory_provider.suspend_action(state, ttl_seconds)
                
                rec = Recommendation(
                    proposed_request=proposed,
                    nonce=nonce,
                    structured_data={
                        "message": f"Found {item['open_exceptions']} open exceptions. Would you like to resolve them?",
                        "action_type": "RESOLVE_EXCEPTIONS"
                    }
                )
                decision.recommendations.append(rec)
                
                # Only produce one recommendation to avoid spam
                break
                
        return decision
