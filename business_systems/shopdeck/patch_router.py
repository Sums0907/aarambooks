import sys

path_router = '/Users/sumatidhingra/aarambooks/business_systems/shopdeck/backend/api/routers/ndr_queue.py'
with open(path_router, 'r') as f:
    content = f.read()

# 1. Update imports
if "get_current_user_edit" not in content:
    content = content.replace("get_current_user", "get_current_user, get_current_user_edit")

# 2. Update claim_queue_item to pass claimer_id from auth payload
old_claim = """async def claim_queue_item(
    request: NDRClaimRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
):
    \"\"\"Brain claims one queue item. Real-time eligibility logic is owned by ShopDeck.\"\"\"
    item = await repo.claim_next_eligible(request.claimer_id, request.lease_seconds)"""
new_claim = """async def claim_queue_item(
    request: NDRClaimRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
    user: dict = Depends(get_current_user),
):
    \"\"\"Brain claims one queue item. Real-time eligibility logic is owned by ShopDeck.\"\"\"
    claimer_id = user.get("sub", request.claimer_id)
    item = await repo.claim_next_eligible(claimer_id, request.lease_seconds)"""
content = content.replace(old_claim, new_claim)

# 3. Update update_queue_status to use get_current_user_edit
old_update = """@router.put("/{queue_item_id}/status", response_model=QueueStatusUpdateResponse,
            dependencies=[Depends(get_current_user)])
async def update_queue_status(
    queue_item_id: str,
    request: QueueStatusUpdateRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
):"""
new_update = """@router.put("/{queue_item_id}/status", response_model=QueueStatusUpdateResponse)
async def update_queue_status(
    queue_item_id: str,
    request: QueueStatusUpdateRequest,
    repo: NDRQueueRepository = Depends(_get_queue_repo),
    user: dict = Depends(get_current_user_edit),
):
    claimer_id = user.get("sub")"""
content = content.replace(old_update, new_update)

old_fail = """            updated = await repo.apply_failure(
                queue_item_id, request.failure_class, request.failure_reason
            )"""
new_fail = """            updated = await repo.apply_failure(
                queue_item_id, request.failure_class, request.failure_reason, claimer_id
            )"""
content = content.replace(old_fail, new_fail)

old_trans = """        updated = await repo.transition_status(queue_item_id, request.status, extra or None)"""
new_trans = """        updated = await repo.transition_status(queue_item_id, request.status, claimer_id, extra or None)"""
content = content.replace(old_trans, new_trans)

# 4. Rewrite register_engagement
import re
engagement_pattern = re.compile(r'@engagement_router\.post\("/engagements".*?return EngagementRegistrationResponse\([^)]+\)', re.DOTALL)

new_engagement = """@engagement_router.post("/engagements", response_model=EngagementRegistrationResponse,
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
        raise HTTPException(status_code=409, detail=str(e))"""
content = engagement_pattern.sub(new_engagement, content)

# 5. Rewrite persist_intelligence_result
intel_pattern = re.compile(r'@intelligence_router\.post\("/intelligence_results".*?return NDRIntelligenceResponse\([^)]+\)', re.DOTALL)

new_intel = """@intelligence_router.post("/intelligence_results", response_model=NDRIntelligenceResponse,
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
        raise HTTPException(status_code=409, detail=str(e))"""
content = intel_pattern.sub(new_intel, content)

with open(path_router, 'w') as f:
    f.write(content)
