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

def _is_valid_correlation(cand: Any) -> bool:
    if not isinstance(cand, str):
        return False
    parts = cand.split("|")
    return len(parts) >= 2 and bool(parts[0]) and bool(parts[1])

def parse_correlation_metadata(payload: dict) -> Tuple[Optional[str], Optional[str]]:
    """Extracts engagement_id and action_request_id defensively, rejecting ambiguity."""
    candidates = set()
    
    # 1. custom_parameters.CustomField
    cp = payload.get("custom_parameters")
    if isinstance(cp, dict) and "CustomField" in cp:
        val = cp.get("CustomField")
        if _is_valid_correlation(val):
            candidates.add(val)
            
    # 2. raw string custom_parameters
    if isinstance(cp, str):
        if _is_valid_correlation(cp):
            candidates.add(cp)
            
    # 3. external_id
    ext = payload.get("external_id")
    if _is_valid_correlation(ext):
        candidates.add(ext)
        
    # 4. root CustomField
    root_cf = payload.get("CustomField")
    if _is_valid_correlation(root_cf):
        candidates.add(root_cf)
        
    if len(candidates) > 1:
        raise HTTPException(status_code=400, detail="Ambiguous correlation fields")
        
    if len(candidates) == 1:
        cand = candidates.pop()
        parts = cand.split("|")
        return parts[0], parts[1]
        
    return None, None

def extract_provider_session_id(payload: dict) -> Optional[str]:
    meta_sid = payload.get("metadata", {}).get("call_sid") if isinstance(payload.get("metadata"), dict) else None
    root_sid = payload.get("CallSid")
    
    if meta_sid and root_sid and meta_sid != root_sid:
        raise HTTPException(status_code=400, detail="Ambiguous provider session ID")
        
    return meta_sid or root_sid

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
    
    call_sid = extract_provider_session_id(payload)
    engagement_id, action_request_id = parse_correlation_metadata(payload)
    
    if not engagement_id:
        raise HTTPException(status_code=400, detail="Missing CustomField correlation")
        
    engagement = await repo.get_engagement(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
        
    # Establishes CallSid -> engagement mapping. Updates any orphan events retroactively.
    if call_sid:
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

async def resolve_correlation(call_sid: Optional[str], payload: dict, repo: CustomerEngagementRepository) -> Optional[str]:
    """Resolves engagement_id from payload correlation, falling back to CallSid lookup."""
    try:
        engagement_id, _ = parse_correlation_metadata(payload)
        if engagement_id:
            return engagement_id
    except HTTPException:
        pass
        
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
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
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
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
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
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
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
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
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
