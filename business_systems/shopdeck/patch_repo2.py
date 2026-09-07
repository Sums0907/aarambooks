import sys

path_repo = '/Users/sumatidhingra/aarambooks/business_systems/shopdeck/backend/api/repositories/ndr_queue.py'
with open(path_repo, 'r') as f:
    content = f.read()

atomic_register = """    async def register_engagement_atomic(
        self,
        queue_item_id: str,
        engagement_id: str,
        idempotency_key: str,
        claimer_id: str,
    ) -> dict:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM ndr_queue WHERE queue_item_id = $1 FOR UPDATE",
                    queue_item_id
                )
                if not row:
                    raise LookupError("Queue item not found")
                if row["claimed_by"] != claimer_id:
                    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")
                if row["queue_status"] != "claimed":
                    raise ValueError(f"Queue item is {row['queue_status']}, must be 'claimed'")

                existing_by_key = await conn.fetchrow(
                    "SELECT * FROM ndr_engagements WHERE idempotency_key = $1",
                    idempotency_key
                )
                if existing_by_key:
                    return {"status": "existing", "engagement_id": existing_by_key["engagement_id"]}

                active = await conn.fetchrow(
                    "SELECT * FROM ndr_engagements WHERE queue_item_id = $1 AND is_active = TRUE FOR UPDATE",
                    queue_item_id
                )
                if active:
                    if active["call_sid"] is not None:
                        raise ValueError("engagement_already_registered: an active engagement with a placed call exists")
                    return {"status": "existing", "engagement_id": active["engagement_id"]}

                engagement = await conn.fetchrow(\"\"\"
                    INSERT INTO ndr_engagements (engagement_id, queue_item_id, awb_no, idempotency_key)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                \"\"\", engagement_id, queue_item_id, row["awb_no"], idempotency_key)

                await conn.execute(\"\"\"
                    UPDATE ndr_queue SET queue_status = 'engagement_registered', updated_at = NOW()
                    WHERE queue_item_id = $1
                \"\"\", queue_item_id)
                return {"status": "created", "engagement_id": engagement["engagement_id"]}
"""

if "async def register_engagement_atomic" not in content:
    content = content + "\n" + atomic_register

atomic_persist = """    async def persist_intelligence_atomic(
        self,
        request_data: dict,
        claimer_id: str,
    ) -> dict:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM ndr_queue WHERE queue_item_id = $1 FOR UPDATE",
                    request_data["queue_item_id"]
                )
                if not row:
                    raise LookupError("Queue item not found")
                if row["claimed_by"] != claimer_id:
                    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")

                existing = await conn.fetchrow("SELECT * FROM ndr_intelligence_results WHERE result_id = $1", request_data["result_id"])
                if existing:
                    IMMUTABLE = ("recommended_action", "diagnosis", "customer_intent", "confidence_level", "provenance")
                    for field in IMMUTABLE:
                        if existing[field] != request_data.get(field):
                            raise ValueError(f"conflicting_result: field '{field}' differs")
                    
                    import json
                    if existing["action_parameters"] != json.dumps(request_data.get("action_parameters", {})):
                        raise ValueError(f"conflicting_result: field 'action_parameters' differs")
                        
                    return {"status": "duplicate", "result_id": existing["result_id"]}
                
                existing_by_eng = await conn.fetchrow("SELECT * FROM ndr_intelligence_results WHERE engagement_id = $1", request_data["engagement_id"])
                if existing_by_eng:
                    raise ValueError(f"engagement_already_has_result")
                    
                import json
                await conn.execute(\"\"\"
                    INSERT INTO ndr_intelligence_results (
                        result_id, queue_item_id, engagement_id, awb_no,
                        recommended_action, diagnosis, customer_intent, confidence_level, provenance,
                        action_parameters, reasoning, risk_score, source_evidence, submitted_by
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                \"\"\",
                    request_data["result_id"], request_data["queue_item_id"], request_data["engagement_id"],
                    request_data["awb_no"], request_data["recommended_action"], request_data.get("diagnosis"),
                    request_data.get("customer_intent"), request_data.get("confidence_level"),
                    request_data.get("provenance"), json.dumps(request_data.get("action_parameters", {})),
                    request_data.get("reasoning"), request_data.get("risk_score"),
                    json.dumps(request_data.get("source_evidence", [])), request_data.get("submitted_by"),
                )
                
                await conn.execute(\"\"\"
                    UPDATE ndr_queue SET queue_status = 'action_ready', action_ready_at = NOW(), updated_at = NOW()
                    WHERE queue_item_id = $1
                \"\"\", request_data["queue_item_id"])
                
                return {"status": "persisted", "result_id": request_data["result_id"]}
"""

if "async def persist_intelligence_atomic" not in content:
    content = content + "\n" + atomic_persist

with open(path_repo, 'w') as f:
    f.write(content)
