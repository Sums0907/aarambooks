"""
NDR Queue Repository — data access layer for the ShopDeck BS NDR Queue.
All SQL is here. No SQL lives in the service or router layers.
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
import asyncpg


VALID_STATUSES = frozenset({
    "eligible", "claimed", "engagement_registered", "call_dispatched",
    "call_completed", "intelligence_pending", "intelligence_received",
    "action_ready", "failed_retryable", "permanently_failed",
    "intelligence_no_action",
})

BUSINESS_FAILURE_CLASSES = frozenset({
    "call_failed", "customer_unreachable", "customer_declined",
    "intelligence_failed", "persistence_failed",
})


class NDRQueueRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------
    async def enroll_eligible_ndrs(self, max_claim_attempts: int = 5, max_retries: int = 2) -> int:
        """
        Scan shipment_ndr_reports for eligible NDRs and insert into ndr_queue.
        Uses DISTINCT ON to deduplicate source rows (no unique constraint on source table).
        INSERT ... ON CONFLICT DO NOTHING ensures idempotency.
        Returns the count of newly enrolled items.
        """
        sql = """
        INSERT INTO ndr_queue (
            awb_no, ndr_attempt_seq, ndr_time_at_enroll,
            ndr_reason_at_enroll, ndr_count_at_enroll, payment_mode,
            max_claim_attempts, max_retries
        )
        SELECT
            snr.awb_no,
            snr.ndr_count          AS ndr_attempt_seq,
            snr.latest_ndr_time    AS ndr_time_at_enroll,
            snr.latest_ndr_reason  AS ndr_reason_at_enroll,
            snr.ndr_count          AS ndr_count_at_enroll,
            snr.payment_mode,
            $1                     AS max_claim_attempts,
            $2                     AS max_retries
        FROM (
            SELECT DISTINCT ON (awb_no, ndr_count)
                awb_no, ndr_count, latest_ndr_time, latest_ndr_reason, payment_mode,
                order_status, ndr_status, delivery_time
            FROM shipment_ndr_reports
            ORDER BY awb_no, ndr_count DESC
        ) snr
        INNER JOIN (
            SELECT DISTINCT awb_no, customer_number
            FROM customer_info
            WHERE customer_number IS NOT NULL AND customer_number <> ''
        ) ci ON ci.awb_no = snr.awb_no
        WHERE snr.ndr_status     = 'pending'
          AND snr.order_status   = 'dispatched'
          AND snr.payment_mode   = 'cod'
          AND snr.delivery_time  IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM ndr_queue q
              WHERE q.awb_no = snr.awb_no
                AND q.ndr_attempt_seq = snr.ndr_count
          )
        ON CONFLICT (awb_no, ndr_attempt_seq) DO NOTHING
        """
        async with self.pool.acquire() as conn:
            status = await conn.execute(sql, max_claim_attempts, max_retries)
        # status string is like "INSERT 0 N"
        try:
            return int(status.split()[-1])
        except Exception:
            return 0

    async def mark_terminal_ndrs(self) -> int:
        """
        Mark queue items as permanently_failed when shipment has become terminal.
        Runs after every sync cycle to catch deliveries/RTOs that happened mid-queue.
        """
        sql = """
        UPDATE ndr_queue q
        SET queue_status       = 'permanently_failed',
            last_failure_class = 'shipment_terminal',
            last_failure_reason = 'Shipment reached terminal state while in queue',
            terminal_at        = NOW(),
            updated_at         = NOW()
        FROM (
            SELECT DISTINCT ON (awb_no) awb_no, order_status, delivery_time, ndr_status
            FROM shipment_ndr_reports
            ORDER BY awb_no, ndr_count DESC
        ) snr
        WHERE q.awb_no = snr.awb_no
          AND q.queue_status NOT IN ('action_ready', 'permanently_failed')
          AND (
              snr.delivery_time IS NOT NULL
              OR snr.order_status IN ('rto_initiated', 'rto_delivered', 'rto_acknowledged')
              OR snr.ndr_status IN ('delivered', 'rto_initiated', 'rto_requested')
          )
        """
        async with self.pool.acquire() as conn:
            status = await conn.execute(sql)
        try:
            return int(status.split()[-1])
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Claim
    # ------------------------------------------------------------------
    async def claim_next_eligible(self, claimer_id: str, lease_seconds: int) -> Optional[Dict[str, Any]]:
        """
        Atomically claim one eligible queue item using SELECT FOR UPDATE SKIP LOCKED.
        Expired leases are reclaimable. claim_attempt_count is always incremented.
        Returns None if no eligible item.
        """
        sql = """
        WITH candidate AS (
            SELECT q.queue_item_id FROM ndr_queue q
            INNER JOIN (
                SELECT DISTINCT ON (awb_no) awb_no, order_status, delivery_time, ndr_status, payment_mode
                FROM shipment_ndr_reports
                ORDER BY awb_no, ndr_count DESC
            ) snr ON snr.awb_no = q.awb_no
            WHERE (
                q.queue_status = 'eligible'
                OR (
                    q.queue_status IN ('claimed', 'failed_retryable')
                    AND q.lease_expires_at < NOW()
                )
            )
            AND q.claim_attempt_count < q.max_claim_attempts
            AND snr.ndr_status = 'pending'
            AND snr.order_status = 'dispatched'
            AND snr.payment_mode = 'cod'
            AND snr.delivery_time IS NULL
            ORDER BY q.ndr_attempt_seq ASC, q.ndr_time_at_enroll ASC
            LIMIT 1
            FOR UPDATE OF q SKIP LOCKED
        )
        UPDATE ndr_queue
        SET queue_status        = 'claimed',
            claimed_by          = $1,
            claimed_at          = NOW(),
            lease_expires_at    = NOW() + make_interval(secs => $2),
            claim_attempt_count = claim_attempt_count + 1,
            updated_at          = NOW()
        FROM candidate
        WHERE ndr_queue.queue_item_id = candidate.queue_item_id
        RETURNING *
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(sql, claimer_id, lease_seconds)
                if row is None:
                    # Check if any items exist that are exhausted — auto-terminate them
                    await conn.execute("""
                        UPDATE ndr_queue
                        SET queue_status = 'permanently_failed',
                            last_failure_class = 'policy_expired',
                            last_failure_reason = 'max_claim_attempts exhausted',
                            terminal_at = NOW(),
                            updated_at = NOW()
                        WHERE queue_status NOT IN ('action_ready', 'permanently_failed')
                          AND claim_attempt_count >= max_claim_attempts
                    """)
                return dict(row) if row else None

    async def get_queue_item(self, queue_item_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ndr_queue WHERE queue_item_id = $1",
                queue_item_id
            )
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
        "engagement_registered": ["claimed"],
        "call_dispatched":       ["engagement_registered"],
        "call_completed":        ["call_dispatched"],
        "intelligence_pending":  ["call_completed"],
        # intelligence_received and action_ready are set ONLY by ShopDeck internally
        "failed_retryable":      [
            "claimed", "engagement_registered", "call_dispatched",
            "call_completed", "intelligence_pending"
        ],
        # Terminal, non-retry disposition: Brain's intelligence layer determined this
        # item needs no further calling (already resolved, policy-blocked, insufficient
        # evidence, or an intelligence-pipeline failure - the specific reason is recorded
        # in last_failure_class/last_failure_reason, not encoded in this status itself).
        # Deliberately NOT reachable from claim_next_eligible()'s claimable set, so it is
        # never silently retried the way failed_retryable would be.
        "intelligence_no_action": [
            "claimed", "engagement_registered", "call_dispatched",
            "call_completed", "intelligence_pending"
        ],
    }

    async def transition_status(
        self,
        queue_item_id: str,
        new_status: str,
        claimer_id: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validates and applies a Brain-callable state transition.
        Raises ValueError for invalid transitions.
        Brain CANNOT set action_ready or permanently_failed.
        """
        if new_status not in self.ALLOWED_TRANSITIONS:
            raise ValueError(f"Brain may not directly set status '{new_status}'")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM ndr_queue WHERE queue_item_id = $1 FOR UPDATE",
                    queue_item_id
                )
                if not row:
                    raise LookupError(f"Queue item {queue_item_id} not found")

                if row["claimed_by"] != claimer_id:
                    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")

                current = row["queue_status"]
                allowed_from = self.ALLOWED_TRANSITIONS[new_status]
                if current not in allowed_from:
                    raise ValueError(
                        f"Invalid transition: {current} → {new_status}. "
                        f"Allowed from: {allowed_from}"
                    )

                updates: Dict[str, Any] = {
                    "queue_status": new_status,
                    "updated_at": "NOW()",
                }
                if extra_fields:
                    updates.update(extra_fields)

                # Build SET clause excluding NOW() literal
                params: List[Any] = []
                set_parts: List[str] = []
                for k, v in updates.items():
                    if v == "NOW()":
                        set_parts.append(f"{k} = NOW()")
                    else:
                        params.append(v)
                        set_parts.append(f"{k} = ${len(params)}")

                params.append(queue_item_id)
                sql = f"""
                    UPDATE ndr_queue SET {', '.join(set_parts)}
                    WHERE queue_item_id = ${len(params)}
                    RETURNING *
                """
                updated = await conn.fetchrow(sql, *params)
                return dict(updated)

    async def apply_failure(
        self,
        queue_item_id: str,
        failure_class: str,
        failure_reason: str,
        claimer_id: str,
    ) -> Dict[str, Any]:
        """
        Marks an item as failed_retryable or permanently_failed.
        Business failure classes increment retry_count.
        Crash/lease_expiry does NOT increment retry_count (handled by claim_attempt_count).
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM ndr_queue WHERE queue_item_id = $1 FOR UPDATE",
                    queue_item_id
                )
                if not row:
                    raise LookupError(f"Queue item {queue_item_id} not found")

                if row["claimed_by"] != claimer_id:
                    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")

                is_business_failure = failure_class in BUSINESS_FAILURE_CLASSES
                new_retry_count = row["retry_count"] + (1 if is_business_failure else 0)
                max_retries = row["max_retries"]

                if new_retry_count >= max_retries and is_business_failure:
                    new_status = "permanently_failed"
                    terminal_sql_part = ", terminal_at = NOW()"
                elif row["claim_attempt_count"] >= row["max_claim_attempts"]:
                    new_status = "permanently_failed"
                    terminal_sql_part = ", terminal_at = NOW()"
                else:
                    new_status = "failed_retryable" if new_status != "permanently_failed" else "permanently_failed"
                    new_status = "failed_retryable"
                    terminal_sql_part = ""

                updated = await conn.fetchrow(f"""
                    UPDATE ndr_queue
                    SET queue_status        = $1,
                        retry_count         = $2,
                        last_failure_class  = $3,
                        last_failure_reason = $4,
                        updated_at          = NOW()
                        {terminal_sql_part}
                    WHERE queue_item_id = $5
                    RETURNING *
                """, new_status, new_retry_count, failure_class, failure_reason, queue_item_id)
                return dict(updated)

    async def set_action_ready(self, queue_item_id: str) -> None:
        """Internal: automatically called by ShopDeck after intelligence persistence."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE ndr_queue
                SET queue_status   = 'action_ready',
                    action_ready_at = NOW(),
                    updated_at     = NOW()
                WHERE queue_item_id = $1
            """, queue_item_id)

    # ------------------------------------------------------------------
    # Engagement
    # ------------------------------------------------------------------
    async def get_active_engagement(self, queue_item_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ndr_engagements WHERE queue_item_id = $1 AND is_active = TRUE",
                queue_item_id
            )
        return dict(row) if row else None

    async def get_engagement_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ndr_engagements WHERE idempotency_key = $1",
                idempotency_key
            )
        return dict(row) if row else None

    async def create_engagement(
        self, engagement_id: str, queue_item_id: str, awb_no: str, idempotency_key: str
    ) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO ndr_engagements (engagement_id, queue_item_id, awb_no, idempotency_key)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            """, engagement_id, queue_item_id, awb_no, idempotency_key)
        return dict(row)

    async def update_engagement(self, engagement_id: str, **fields: Any) -> Dict[str, Any]:
        params: List[Any] = []
        set_parts: List[str] = []
        for k, v in fields.items():
            params.append(v)
            set_parts.append(f"{k} = ${len(params)}")
        set_parts.append("updated_at = NOW()")
        params.append(engagement_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE ndr_engagements SET {', '.join(set_parts)} WHERE engagement_id = ${len(params)} RETURNING *",
                *params
            )
        return dict(row)

    async def deactivate_engagement(self, engagement_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE ndr_engagements SET is_active = FALSE, updated_at = NOW() WHERE engagement_id = $1",
                engagement_id
            )

    # ------------------------------------------------------------------
    # Intelligence
    # ------------------------------------------------------------------
    IMMUTABLE_INTELLIGENCE_FIELDS = (
        "recommended_action", "diagnosis", "customer_intent", "confidence_level", "provenance"
    )

    async def get_intelligence_by_result_id(self, result_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ndr_intelligence_results WHERE result_id = $1", result_id
            )
        return dict(row) if row else None

    async def get_intelligence_by_engagement_id(self, engagement_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ndr_intelligence_results WHERE engagement_id = $1", engagement_id
            )
        return dict(row) if row else None

    async def create_intelligence_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO ndr_intelligence_results (
                    result_id, queue_item_id, engagement_id, awb_no,
                    recommended_action, diagnosis, customer_intent, confidence_level, provenance,
                    action_parameters, reasoning, risk_score, source_evidence, submitted_by
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                RETURNING *
            """,
                data["result_id"],
                data["queue_item_id"],
                data["engagement_id"],
                data["awb_no"],
                data["recommended_action"],
                data.get("diagnosis"),
                data.get("customer_intent"),
                data.get("confidence_level"),
                data.get("provenance"),
                json.dumps(data.get("action_parameters", {})),
                data.get("reasoning"),
                data.get("risk_score"),
                json.dumps(data.get("source_evidence", [])),
                data.get("submitted_by"),
            )
        return dict(row)

    # ------------------------------------------------------------------
    # ACTION_READY query
    # ------------------------------------------------------------------
    async def get_action_ready_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    q.queue_item_id,
                    q.awb_no,
                    q.ndr_attempt_seq,
                    q.ndr_reason_at_enroll,
                    q.action_ready_at,
                    snr.customer_name,
                    ir.recommended_action,
                    ir.action_parameters,
                    ir.customer_intent,
                    ir.diagnosis,
                    ir.confidence_level,
                    ir.persisted_at  AS intelligence_at,
                    e.engagement_id
                FROM ndr_queue q
                JOIN ndr_engagements e ON e.queue_item_id = q.queue_item_id AND e.is_active = TRUE
                JOIN ndr_intelligence_results ir ON ir.engagement_id = e.engagement_id
                LEFT JOIN (
                    SELECT DISTINCT ON (awb_no) awb_no, customer_name
                    FROM shipment_ndr_reports
                    ORDER BY awb_no, ndr_count DESC
                ) snr ON snr.awb_no = q.awb_no
                WHERE q.queue_status = 'action_ready'
                ORDER BY q.action_ready_at DESC
                LIMIT $1
            """, limit)
        return [dict(r) for r in rows]

    async def register_engagement_atomic(
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
                    raise ValueError("engagement_outcome_unknown: an active engagement exists but call_sid is unknown. Awaiting webhook reconciliation or timeout.")

                engagement = await conn.fetchrow("""
                    INSERT INTO ndr_engagements (engagement_id, queue_item_id, awb_no, idempotency_key)
                    VALUES ($1, $2, $3, $4)
                    RETURNING *
                """, engagement_id, queue_item_id, row["awb_no"], idempotency_key)

                await conn.execute("""
                    UPDATE ndr_queue SET queue_status = 'engagement_registered', updated_at = NOW()
                    WHERE queue_item_id = $1
                """, queue_item_id)
                return {"status": "created", "engagement_id": engagement["engagement_id"]}

    async def persist_intelligence_atomic(
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
                await conn.execute("""
                    INSERT INTO ndr_intelligence_results (
                        result_id, queue_item_id, engagement_id, awb_no,
                        recommended_action, diagnosis, customer_intent, confidence_level, provenance,
                        action_parameters, reasoning, risk_score, source_evidence, submitted_by
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                """,
                    request_data["result_id"], request_data["queue_item_id"], request_data["engagement_id"],
                    request_data["awb_no"], request_data["recommended_action"], request_data.get("diagnosis"),
                    request_data.get("customer_intent"), request_data.get("confidence_level"),
                    request_data.get("provenance"), json.dumps(request_data.get("action_parameters", {})),
                    request_data.get("reasoning"), request_data.get("risk_score"),
                    json.dumps(request_data.get("source_evidence", [])), request_data.get("submitted_by"),
                )
                
                await conn.execute("""
                    UPDATE ndr_queue SET queue_status = 'action_ready', action_ready_at = NOW(), updated_at = NOW()
                    WHERE queue_item_id = $1
                """, request_data["queue_item_id"])
                
                return {"status": "persisted", "result_id": request_data["result_id"]}
