import sys
import json
import re

path_repo = '/Users/sumatidhingra/aarambooks/business_systems/shopdeck/backend/api/repositories/ndr_queue.py'
with open(path_repo, 'r') as f:
    content = f.read()

# 1. Update claim_next_eligible with live guard
old_claim = """        WITH candidate AS (
            SELECT queue_item_id FROM ndr_queue
            WHERE (
                queue_status = 'eligible'
                OR (
                    queue_status IN ('claimed', 'failed_retryable')
                    AND lease_expires_at < NOW()
                )
            )
            AND claim_attempt_count < max_claim_attempts
            ORDER BY ndr_attempt_seq ASC, ndr_time_at_enroll ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )"""

new_claim = """        WITH candidate AS (
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
        )"""

content = content.replace(old_claim, new_claim)

# 2. Update transition_status
old_transition = """    async def transition_status(
        self,
        queue_item_id: str,
        new_status: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:"""
new_transition = """    async def transition_status(
        self,
        queue_item_id: str,
        new_status: str,
        claimer_id: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:"""
content = content.replace(old_transition, new_transition)

old_check = """                if not row:
                    raise LookupError(f"Queue item {queue_item_id} not found")

                current = row["queue_status"]"""
new_check = """                if not row:
                    raise LookupError(f"Queue item {queue_item_id} not found")

                if row["claimed_by"] != claimer_id:
                    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")

                current = row["queue_status"]"""
content = content.replace(old_check, new_check)

# 3. Update apply_failure
old_apply_failure = """    async def apply_failure(
        self,
        queue_item_id: str,
        failure_class: str,
        failure_reason: str,
    ) -> Dict[str, Any]:"""
new_apply_failure = """    async def apply_failure(
        self,
        queue_item_id: str,
        failure_class: str,
        failure_reason: str,
        claimer_id: str,
    ) -> Dict[str, Any]:"""
content = content.replace(old_apply_failure, new_apply_failure)

old_failure_check = """                if not row:
                    raise LookupError(f"Queue item {queue_item_id} not found")

                is_business_failure = failure_class in BUSINESS_FAILURE_CLASSES"""
new_failure_check = """                if not row:
                    raise LookupError(f"Queue item {queue_item_id} not found")

                if row["claimed_by"] != claimer_id:
                    raise PermissionError(f"Caller {claimer_id} cannot mutate item claimed by {row['claimed_by']}")

                is_business_failure = failure_class in BUSINESS_FAILURE_CLASSES"""
content = content.replace(old_failure_check, new_failure_check)


with open(path_repo, 'w') as f:
    f.write(content)


print("Repo patched successfully")
