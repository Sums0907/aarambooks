"""
NDR Queue Router — Brain-facing API for the ShopDeck BS NDR Queue.

Ownership:
- ShopDeck owns: queue state, eligibility, claim/lease, engagement records,
  intelligence persistence, ACTION_READY transition.
- Brain: claims work, registers engagements, reports status, submits intelligence.
- Brain CANNOT directly set: action_ready, permanently_failed.
"""
from __future__ import annotations
import json
import httpx
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import asyncpg

from ..dependencies import get_db_pool, get_ndr_service
from ..auth import get_current_user, get_current_user_edit
from ..repositories.ndr_queue import NDRQueueRepository
from ..schemas.ndr_queue import (
    NDRClaimRequest, NDRClaimResponse,
    EngagementRegistrationRequest, EngagementRegistrationResponse,
    QueueStatusUpdateRequest, QueueStatusUpdateResponse,
    NDRIntelligenceRequest, NDRIntelligenceResponse,
    ActionReadyItem, EnrollResponse,
)

router = APIRouter(prefix="/api/v1/ndr/queue", tags=["NDR Queue"])
intelligence_router = APIRouter(prefix="/api/v1/ndr", tags=["NDR Intelligence"])
engagement_router = APIRouter(prefix="/api/v1/ndr", tags=["NDR Engagements"])


def _get_queue_repo(pool: asyncpg.Pool = Depends(get_db_pool)) -> NDRQueueRepository:
    return NDRQueueRepository(pool)


async def _fetch_ndr_context(awb_no: str) -> Optional[Dict[str, Any]]:
    """Fetch NDR context from the ShopDeck BS API (not directly from DB)."""
    shopdeck_url = os.environ.get("DATABASE_URL", "")  # unused
    api_base = os.environ.get("SHOPDECK_SELF_API_URL", "http://localhost:8000")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_base}/api/v1/ndr/{awb_no}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


# ------------------------------------------------------------------
# CLAIM
# ------------------------------------------------------------------
@router.post("/claim", response_model=NDRClaimResponse, dependencies=[Depends(get_current_user)])
async def claim_queue_item(
    request: NDRClaimRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
):
    """
    Atomically claim the next eligible NDR queue item.
    Returns HTTP 204 if no item is available.
    AWB is queue-selected — no operator-supplied AWB.
    """
    item = await repo.claim_next_eligible(request.claimer_id, request.lease_seconds)
    if item is None:
        raise HTTPException(status_code=204, detail="No eligible NDR queue item available")

    # Attach any existing active engagement so Brain can determine prior state
    active_engagement = await repo.get_active_engagement(str(item["queue_item_id"]))

    # Fetch the NDR context (via API — not direct DB)
    ndr_context = await _fetch_ndr_context(item["awb_no"])

    return NDRClaimResponse(
        queue_item_id=str(item["queue_item_id"]),
        awb_no=item["awb_no"],
        ndr_attempt_seq=item["ndr_attempt_seq"],
        ndr_time_at_enroll=item["ndr_time_at_enroll"],
        ndr_reason_at_enroll=item["ndr_reason_at_enroll"],
        payment_mode=item["payment_mode"],
        current_engagement=active_engagement,
        ndr_context=ndr_context,
    )


# ------------------------------------------------------------------
# STATUS UPDATE
# ------------------------------------------------------------------
@router.patch("/{queue_item_id}/status", response_model=QueueStatusUpdateResponse)
async def update_queue_status(
    queue_item_id: str,
    request: QueueStatusUpdateRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
    user: dict = Depends(get_current_user_edit),
):
    """
    Brain reports status transitions. Enforces valid transition matrix.
    Brain CANNOT set action_ready or permanently_failed.
    """
    claimer_id = user.get("sub")
    try:
        if request.status == "failed_retryable":
            updated = await repo.apply_failure(
                queue_item_id,
                claimer_id=claimer_id,
                failure_class=request.failure_class or "call_failed",
                failure_reason=request.failure_reason or "Brain reported failure",
            )
            will_retry = updated["queue_status"] == "failed_retryable"
            return QueueStatusUpdateResponse(
                queue_item_id=queue_item_id,
                queue_status=updated["queue_status"],
                will_retry=will_retry,
            )

        # Build extra_fields for engagement/call updates
        extra: Dict[str, Any] = {}
        if request.status == "call_dispatched" and request.call_sid:
            # Update engagement with call_sid
            if request.engagement_id:
                await repo.update_engagement(
                    request.engagement_id,
                    call_sid=request.call_sid,
                    dispatched_at="NOW()",  # handled separately
                )
                async with (await _get_raw_pool(repo)).acquire() as conn:
                    await conn.execute(
                        "UPDATE ndr_engagements SET dispatched_at = NOW(), updated_at = NOW() WHERE engagement_id = $1",
                        request.engagement_id
                    )

        if request.status == "call_completed" and request.engagement_id:
            await repo.update_engagement(
                request.engagement_id,
                call_outcome=request.call_outcome,
                transcript_id=request.transcript_id,
                transcript_summary=request.transcript_summary,
                completed_at=None,  # will be set via raw update below
            )
            async with (await _get_raw_pool(repo)).acquire() as conn:
                await conn.execute("""
                    UPDATE ndr_engagements
                    SET call_outcome = $1, transcript_id = $2, transcript_summary = $3,
                        completed_at = NOW(), updated_at = NOW()
                    WHERE engagement_id = $4
                """, request.call_outcome, request.transcript_id,
                     request.transcript_summary, request.engagement_id)

        updated = await repo.transition_status(queue_item_id, request.status, claimer_id, extra or None)
        return QueueStatusUpdateResponse(
            queue_item_id=queue_item_id,
            queue_status=updated["queue_status"],
        )

    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


async def _get_raw_pool(repo: NDRQueueRepository) -> asyncpg.Pool:
    return repo.pool


# ------------------------------------------------------------------
# ENROLL (admin / test only)
# ------------------------------------------------------------------
@router.post("/enroll", response_model=EnrollResponse, dependencies=[Depends(get_current_user)])
async def admin_enroll(repo: NDRQueueRepository = Depends(_get_queue_repo)):
    """Admin-only: trigger enrollment manually (for testing). Not in normal production path."""
    enrolled = await repo.enroll_eligible_ndrs()
    terminated = await repo.mark_terminal_ndrs()
    return EnrollResponse(enrolled=enrolled, terminated=terminated)


# ------------------------------------------------------------------
# ACTION_READY
# ------------------------------------------------------------------
@router.get("/action_ready", response_model=List[ActionReadyItem],
            dependencies=[Depends(get_current_user)])
async def get_action_ready(
    limit: int = Query(50, ge=1, le=200),
    repo: NDRQueueRepository = Depends(_get_queue_repo),
):
    """Morning review: returns ACTION_READY queue items with intelligence."""
    items = await repo.get_action_ready_items(limit)
    parsed = []
    for i in items:
        d = dict(i)
        d['queue_item_id'] = str(d['queue_item_id'])
        d['engagement_id'] = str(d['engagement_id'])
        if isinstance(d.get('action_parameters'), str):
            import json
            d['action_parameters'] = json.loads(d['action_parameters'])
        parsed.append(ActionReadyItem(**d))
    return parsed


# ------------------------------------------------------------------
# ENGAGEMENT PRE-REGISTRATION
# ------------------------------------------------------------------
@engagement_router.post("/engagements", response_model=EngagementRegistrationResponse,
                        status_code=201)
async def register_engagement(
    request: EngagementRegistrationRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
    user: dict = Depends(get_current_user_edit),
):
    claimer_id = user.get("sub")
    try:
        res = await repo.register_engagement_atomic(
            request.queue_item_id, request.engagement_id, request.idempotency_key, claimer_id
        )
        return EngagementRegistrationResponse(
            engagement_id=res["engagement_id"],
            status=res["status"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ------------------------------------------------------------------
# INTELLIGENCE PERSISTENCE
# ------------------------------------------------------------------
@intelligence_router.post("/intelligence_results", response_model=NDRIntelligenceResponse,
                          status_code=201)
async def persist_intelligence_result(
    request: NDRIntelligenceRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
    user: dict = Depends(get_current_user_edit),
):
    claimer_id = user.get("sub")
    request_data = {
        "result_id":          request.result_id,
        "queue_item_id":      request.queue_item_id,
        "engagement_id":      request.engagement_id,
        "awb_no":             request.awb_no,
        "recommended_action": request.recommended_action,
        "diagnosis":          request.diagnosis,
        "customer_intent":    request.customer_intent,
        "confidence_level":   request.confidence_level,
        "provenance":         request.provenance,
        "action_parameters":  request.action_parameters,
        "reasoning":          request.reasoning,
        "risk_score":         request.risk_score,
        "source_evidence":    request.source_evidence,
        "submitted_by":       request.submitted_by,
    }
    try:
        res = await repo.persist_intelligence_atomic(request_data, claimer_id)
        if res["status"] == "duplicate":
            return JSONResponse(status_code=200, content=res)
        return NDRIntelligenceResponse(status="persisted", result_id=request.result_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
