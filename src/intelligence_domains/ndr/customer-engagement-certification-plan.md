# Customer Engagement Database Wiring - Certification Plan

We will diagnose, fix, and comprehensively certify the database wiring for the V1 Customer Engagement Boundary using a realistic `mongomock_motor` mock.

## Goal
Certify that the repository enforces all lifecycle, idempotency, and state-transition rules, and that webhooks correctly persist data without corrupting state or hanging.

## Proposed Changes

### 1. Diagnosis and Fix of Hanging Tests
**Diagnosis:** The previous tests appeared to "hang" for 30 seconds because `test_exotel_webhooks.py` was not mocking the MongoDB client properly. The webhooks attempted to connect to a real MongoDB instance on `localhost:27017` which the Sandbox blocked, resulting in a 30-second `ServerSelectionTimeoutError` from `motor`.
**Fix:** We will install `mongomock_motor` and patch `get_mongo_db()` globally for the test suite to return an in-memory `AsyncIOMotorClient`.

### 2. Dependency Updates
We will run `pip install mongomock_motor` to provide realistic async MongoDB simulation for the test suite without real database dependencies.

### 3. Repository Tests Expansion
#### [MODIFY] `tests/infrastructure/adapters/customer_engagement/test_repository.py`
We will replace `AsyncMock` with `mongomock_motor` and cover:
- Engagement creation.
- ALL valid state transitions (REQUESTED → DISPATCHED → CONNECTED → IN_PROGRESS → COMPLETED).
- Invalid backward transitions (e.g. COMPLETED → CONNECTED).
- Provider-scoped idempotency via `DuplicateKeyError`.
- Missing `provider_event_id` handled safely via Sparse indexing.
- Atomic state transition behavior via `$in` conditions.
- Normalization state remains independent.

### 4. Webhook Tests Expansion
#### [MODIFY] `tests/api/webhooks/test_exotel_webhooks.py`
We will rewrite the tests using `TestClient` and `mongomock_motor`:
- Complete lifecycle: SESSION-START → TRANSCRIPT → INSIGHTS → SESSION-END.
- Duplicate / out-of-order webhook delivery behavior.
- Validate that session-end does NOT mutate ShopDeck.

### 5. Architectural Invariants Validation
We will ensure that the Webhooks and Executor tests prove the separation of concerns: Exotel is purely observational, and Brain Normalization does not occur synchronously in the webhook.

## Verification Plan
1. Execute `pytest tests/infrastructure/adapters/customer_engagement`
2. Execute `pytest tests/api/webhooks`
3. Execute `pytest tests/intelligence_domains/ndr`
4. Confirm test completion time drops from 30+ seconds to < 2 seconds.
5. Provide the Certification Report.
