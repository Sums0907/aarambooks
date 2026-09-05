from fastapi import APIRouter, Request, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional, Tuple
import hmac
from datetime import datetime, UTC

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementEvent, EngagementState
from src.shared.config import settings

router = APIRouter(prefix="/api/customer-engagement/voice/exotel", tags=["exotel-webhooks"])

security = HTTPBearer()

def verify_exotel_bearer(credentials: HTTPAuthorizationCredentials = Security(security)) -> None:
    """
    Cryptographically verifies the Bearer token against AARAM_EXOTEL_WEBHOOK_SECRET.
    Fails closed if missing, malformed, or invalid.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
    provided_token = credentials.credentials
    expected_token = settings.aaram_exotel_webhook_secret
    
    if not hmac.compare_digest(expected_token.encode('utf-8'), provided_token.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

def parse_correlation_metadata(custom_field: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Extracts engagement_id and action_request_id strictly for initial correlation, NOT authentication."""
    if not custom_field:
        return None, None
    parts = custom_field.split("|")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

def get_repository():
    return CustomerEngagementRepository()

@router.post("/session-start", dependencies=[Depends(verify_exotel_bearer)])
async def handle_session_start(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    """
    Session start webhook.
    Returns ONLY documented session-start response schema.
    """
    payload = await request.json()
    
    custom_field = payload.get("CustomField")
    call_sid = payload.get("CallSid")
    engagement_id, action_request_id = parse_correlation_metadata(custom_field)
    
    if not engagement_id:
        raise HTTPException(status_code=400, detail="Missing CustomField correlation")
        
    engagement = await repo.get_engagement(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
        
    # Establishes CallSid -> engagement mapping. Updates any orphan events retroactively.
    await repo.update_engagement_correlation(engagement_id, session_id=call_sid)
    
    # State transitions are strictly monotonic
    await repo.transition_state(engagement_id, EngagementState.CONNECTED)
    
    greeting_text = "Hello! We noticed a failed delivery attempt for your recent order. Are you available to receive it tomorrow?"
    
    return {
        "response": {
            "data": {
                "greeting message": {
                    "text": greeting_text
                },
                "session constants": {
                    "engagement_id": engagement_id,
                    "action_request_id": action_request_id
                }
            }
        }
    }

async def resolve_correlation(call_sid: str, repo: CustomerEngagementRepository) -> Optional[str]:
    """Resolves engagement_id from CallSid if CustomField is missing."""
    if not call_sid:
        return None
    engagement = await repo.get_engagement_by_provider_correlation(provider="EXOTEL", session_id=call_sid)
    if engagement:
        return engagement.get("engagement_id")
    return None

@router.post("/transcript", dependencies=[Depends(verify_exotel_bearer)])
async def handle_transcript(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = payload.get("CallSid")
    engagement_id = await resolve_correlation(call_sid, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,  # Might be None if out-of-order
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="transcript",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    # log_event safely ignores duplicates
    await repo.log_event(event)
    
    if engagement_id:
        await repo.transition_state(engagement_id, EngagementState.IN_PROGRESS)

    return {"status": "received"}

@router.post("/insights", dependencies=[Depends(verify_exotel_bearer)])
async def handle_insights(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = payload.get("CallSid")
    engagement_id = await resolve_correlation(call_sid, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="insights",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
        
    return {"status": "received"}

@router.post("/session-end", dependencies=[Depends(verify_exotel_bearer)])
async def handle_session_end(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = payload.get("CallSid")
    engagement_id = await resolve_correlation(call_sid, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="session-end",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
    
    if engagement_id:
        status_str = payload.get("Status", "").lower()
        if status_str in ["failed", "busy", "no-answer"]:
            final_state = EngagementState.FAILED
        else:
            final_state = EngagementState.COMPLETED
            
        await repo.transition_state(engagement_id, final_state)

    return {"status": "received"}

@router.post("/pre-agent-transfer", dependencies=[Depends(verify_exotel_bearer)])
async def handle_pre_agent_transfer(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = payload.get("CallSid")
    engagement_id = await resolve_correlation(call_sid, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="pre-agent-transfer",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
    
    if engagement_id:
        await repo.transition_state(engagement_id, EngagementState.ESCALATED)
        
    return {"status": "escalation_registered"}
