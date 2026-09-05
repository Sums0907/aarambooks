from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
from typing import Dict, Any, Optional, Tuple
import hmac
import hashlib
from datetime import datetime, UTC

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementEvent, EngagementState
from src.shared.config import settings

router = APIRouter(prefix="/api/customer-engagement/voice/exotel", tags=["exotel-webhooks"])

def parse_and_verify_correlation_metadata(custom_field: Optional[str]) -> Tuple[str, str]:
    """
    Cryptographically verifies the CustomField originated from Aaram.
    Fails closed if the signature is missing or invalid.
    """
    if not custom_field:
        raise HTTPException(status_code=401, detail="Missing CustomField for authentication")
        
    parts = custom_field.split("|")
    if len(parts) == 3:
        engagement_id, action_request_id, provided_signature = parts
        
        base_custom_field = f"{engagement_id}|{action_request_id}"
        expected_signature = hmac.new(
            settings.aaram_exotel_webhook_secret.encode('utf-8'),
            base_custom_field.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(expected_signature, provided_signature):
            return engagement_id, action_request_id
            
    raise HTTPException(status_code=401, detail="Invalid webhook signature")

async def extract_correlation(request: Request) -> Tuple[str, str]:
    payload = await request.json()
    return parse_and_verify_correlation_metadata(payload.get("CustomField"))

def get_repository():
    # Dependency injection for FastAPI
    return CustomerEngagementRepository()

@router.post("/session-start")
async def handle_session_start(
    request: Request, 
    correlation: Tuple[str, str] = Depends(extract_correlation),
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    """
    Session start webhook.
    Returns ONLY documented session-start response schema.
    """
    payload = await request.json()
    engagement_id, action_request_id = correlation
    call_sid = payload.get("CallSid")
        
    engagement = await repo.get_engagement(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
        
    # Update correlation and transition state
    await repo.update_engagement_correlation(engagement_id, session_id=call_sid)
    
    # State transitions are strictly monotonic in the repository; 
    # if this is a late session-start after a terminal state, transition_state returns False safely.
    await repo.transition_state(engagement_id, EngagementState.CONNECTED)
    
    # Normally we read dynamic constraints from ActionRequest or EngagementRecord
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

@router.post("/transcript")
async def handle_transcript(
    request: Request, 
    correlation: Tuple[str, str] = Depends(extract_correlation),
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    engagement_id, _ = correlation
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        event_type="transcript",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    # log_event safely ignores duplicates (idempotent via sparse index)
    await repo.log_event(event)
    
    # Transcript means the call is in progress. 
    # transition_state mathematically rejects regressions if the state is already terminal (COMPLETED).
    await repo.transition_state(engagement_id, EngagementState.IN_PROGRESS)

    return {"status": "received"}

@router.post("/insights")
async def handle_insights(
    request: Request, 
    correlation: Tuple[str, str] = Depends(extract_correlation),
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    engagement_id, _ = correlation
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        event_type="insights",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
        
    return {"status": "received"}

@router.post("/session-end")
async def handle_session_end(
    request: Request, 
    correlation: Tuple[str, str] = Depends(extract_correlation),
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    """
    Closes the engagement. Sets normalization_status=PENDING.
    DO NOT call Brain synchronously. DO NOT mutate ShopDeck.
    """
    payload = await request.json()
    engagement_id, _ = correlation
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        event_type="session-end",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
    
    status_str = payload.get("Status", "").lower()
    if status_str in ["failed", "busy", "no-answer"]:
        final_state = EngagementState.FAILED
    else:
        final_state = EngagementState.COMPLETED
        
    await repo.transition_state(engagement_id, final_state)
    # Normalization status is already PENDING by default, 
    # so we leave it for the background worker.

    return {"status": "received"}

@router.post("/pre-agent-transfer")
async def handle_pre_agent_transfer(
    request: Request, 
    correlation: Tuple[str, str] = Depends(extract_correlation),
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    engagement_id, _ = correlation
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        event_type="pre-agent-transfer",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
    await repo.transition_state(engagement_id, EngagementState.ESCALATED)
        
    return {"status": "escalation_registered"}
