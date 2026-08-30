from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional
from src.event_bus.receiver import InboundReceiver
from src.security.validator import SecurityValidationError
from src.security.auth import verify_m2m_token
import logging

router = APIRouter(prefix="/api/v1/webhooks", tags=["Inbound Webhooks"])

# This dependency will be overridden in main.py
def get_inbound_receiver() -> InboundReceiver:
    raise NotImplementedError("Dependency not wired")

@router.post("/inbound/internal")
async def receive_internal_event(
    request: Request,
    receiver: InboundReceiver = Depends(get_inbound_receiver),
    claims: dict = Depends(verify_m2m_token)
):
    """
    Physical boundary for INTERNAL trusted webhooks (Inventory, Packing).
    Authenticated via AaramIdentity RS256 M2M JWT.
    """
    try:
        raw_body = await request.body()
        raw_payload = raw_body.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 payload")
        
    try:
        dispatched_str = await receiver.process_raw_payload(raw_payload)
        return {"status": "ACKNOWLEDGED", "dispatched": dispatched_str is not None}
    except SecurityValidationError as e:
        logging.warning(f"Security validation failed for internal event: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Internal error processing internal event: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")

@router.post("/inbound/shiprocket")
async def receive_shiprocket_event(request: Request):
    """
    Physical boundary for Shiprocket external webhooks.
    BLOCKED: Missing Shiprocket webhook signature contract.
    """
    raise HTTPException(status_code=501, detail="Shiprocket authentication contract not established")

@router.post("/inbound/shopdeck")
async def receive_shopdeck_event(request: Request):
    """
    Physical boundary for ShopDeck external webhooks.
    BLOCKED: Missing ShopDeck webhook signature contract.
    """
    raise HTTPException(status_code=501, detail="ShopDeck authentication contract not established")

