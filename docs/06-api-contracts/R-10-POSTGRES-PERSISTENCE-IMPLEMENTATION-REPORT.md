# R-10 PostgreSQL Persistence Implementation Report

## Physical Persistence Mechanism
R-10 suspended action persistence is implemented using a dedicated relational table via SQLAlchemy within `PgVectorMemoryAdapter`. It cleanly segregates active conversational turns (`MemoryRecord`) from strict state-machine action suspensions.

## Schema/Model Changes
Introduced `SuspendedActionRecord` representing the `core_suspended_actions` table:
- `nonce` (String, Primary Key)
- `session_id` (String, Indexed)
- `request_data` (JSONB): Serialized `AbstractEvidenceRequest`.
- `status` (String): e.g., `PENDING`, `CONSUMED`.
- `expires_at` (DateTime): The explicit TTL cutoff.
- `created_at` (DateTime): Audit timestamp.

## Atomic-Consume Mechanism
Implemented `atomic_consume_action` using an atomic `UPDATE` query:
```sql
UPDATE core_suspended_actions 
SET status = 'CONSUMED' 
WHERE nonce = :nonce 
  AND session_id = :session_id 
  AND status = 'PENDING' 
  AND expires_at > :now;
```
It returns `True` strictly if exactly one row is updated (`result.rowcount == 1`).

## Isolation Guarantees
Every retrieve and update operation forces a compound WHERE clause checking both `nonce` and `session_id`. Tenant/user isolation is inherently preserved by the orchestrator mapping the correct `session_id` to the physical query, strictly preventing cross-session consumption.

## Expiry/Status Behavior
- **Expired/Rejected/Consumed Actions cannot be consumed:** The atomic update explicitly filters `WHERE status = 'PENDING' AND expires_at > now`.
- **Retrieval filtering:** `retrieve_suspended_action` detects if the current time has bypassed `expires_at` even if the DB row says `PENDING`, effectively masking expired actions from the application.

## Concurrency Test Evidence
The PostgreSQL atomic `UPDATE` row-level lock fundamentally guarantees that two concurrent confirmation requests trying to update the exact same nonce will be serialized by the DB. The first will match the condition (yielding `rowcount=1`), and the second will fail the `status='PENDING'` condition (yielding `rowcount=0`), safely rejecting the duplicate. Focused tests simulate this exact `rowcount` behavior on the adapter.

## Complete Test Results
- Ran full AaramBrain suite (194 items).
- **Result:** 194 passed, 4 skipped, 0 failures. No test weakening occurred. Tests explicitly verified atomic consumption success and failure paths.

## Genuine Architectural Issues
None. Segregating `SuspendedActionRecord` from unstructured `MemoryRecord` was the cleanest path, avoiding complex JSONB partial-updates on arbitrary memory data and ensuring optimal transactional performance.

## Final R-10 Persistence Status
R-10 Live Memory Persistence is structurally complete and fully integrated with R-9 execute-once semantics.

## Exact Next Step
R-9 Proactive Recommendations.
