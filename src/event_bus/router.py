from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from src.event_bus.receiver import InboundReceiver
from src.security.validator import SecurityValidationError
from src.security.auth import verify_m2m_token
import logging
import json

router = APIRouter(prefix="/api/v1/webhooks", tags=["Inbound Webhooks"])

# This dependency will be overridden in main.py
def get_inbound_receiver() -> InboundReceiver:
    raise NotImplementedError("Dependency not wired")

from src.intelligence_domains.ndr.communication_engine import CommunicationEngine

def get_communication_engine() -> CommunicationEngine:
    raise NotImplementedError("Dependency not wired")

# ── NDR Event Push Router (matches ShopDeck sync patch payload) ──────────────
ndr_event_router = APIRouter(prefix="/events", tags=["NDR Events"])

class NDRPushPayload(BaseModel):
    awb_nos: List[str]
    source: str = "shopdeck_ndr_proxy"

@ndr_event_router.post("/ndr")
async def receive_ndr_event(
    payload: NDRPushPayload,
    receiver: InboundReceiver = Depends(get_inbound_receiver)
):
    """
    [LEGACY_MANUAL_DIAGNOSTIC] NDR Push Receiver.
    This endpoint is DEPRECATED in favor of the ShopDeck BS NDR Queue.
    It should NOT be used in production execution paths.
    """
    logging.warning("🚨 [LEGACY_MANUAL_DIAGNOSTIC] /events/ndr called. This path bypasses the authoritative ShopDeck NDR Queue and should only be used for legacy diagnostics.")
    results = []
    for awb_no in payload.awb_nos:
        try:
            envelope = json.dumps({
                "event_type": "ndr_update",
                "content": {"awb_no": awb_no, "source": payload.source}
            })
            dispatched = await receiver.process_raw_payload(envelope)
            results.append({"awb_no": awb_no, "status": "QUEUED", "dispatched": dispatched is not None})
        except Exception as e:
            logging.error(f"NDR event routing failed for AWB {awb_no}: {e}")
            results.append({"awb_no": awb_no, "status": "FAILED", "error": str(e)})
    return {"status": "ACKNOWLEDGED", "processed": len(results), "results": results}


# ── Customer Reply Webhooks (IVR / WhatsApp) ────────────────────────────────
class WebhookReplyPayload(BaseModel):
    awb_no: str
    message: str

@router.post("/whatsapp")
async def receive_whatsapp_reply(
    payload: WebhookReplyPayload,
    comm_engine: CommunicationEngine = Depends(get_communication_engine)
):
    """Webhook for WhatsApp Business API to push customer replies."""
    interaction_id = await comm_engine.handle_inbound_reply(payload.awb_no, "whatsapp", payload.message)
    return {"status": "ACKNOWLEDGED", "interaction_id": interaction_id}

@router.post("/ivr")
async def receive_ivr_reply(
    payload: WebhookReplyPayload,
    comm_engine: CommunicationEngine = Depends(get_communication_engine)
):
    """Webhook for IVR system to push customer keypad inputs or speech-to-text."""
    interaction_id = await comm_engine.handle_inbound_reply(payload.awb_no, "ivr", payload.message)
    return {"status": "ACKNOWLEDGED", "interaction_id": interaction_id}
# ─────────────────────────────────────────────────────────────────────────────


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
async def receive_shopdeck_event(
    request: Request,
    receiver: InboundReceiver = Depends(get_inbound_receiver)
):
    """
    Physical boundary for ShopDeck NDR webhooks (internal M2M, trusted network).
    Accepts the standard event_type/content envelope from the ShopDeck sync engine.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        dispatched = await receiver.process_raw_payload(json.dumps(body))
        return {"status": "ACKNOWLEDGED", "dispatched": dispatched is not None}
    except SecurityValidationError as e:
        logging.warning(f"Security validation failed for ShopDeck event: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing ShopDeck event: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")
