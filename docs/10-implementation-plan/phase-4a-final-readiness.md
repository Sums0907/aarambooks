# Phase 4A: Final Readiness Audit & Execution Plan

## 1. Executive Status
* **PHASE 4A (Inventory Context):** COMPLETE.
* **PHASE 4B (ShopDeck Context):** BLOCKED (Headless connectivity unavailable).
* **PHASE 4C (AaramPacking Context):** PERMANENTLY OUT OF SCOPE.
* **Overall Phase 4:** Will be marked PARTIALLY COMPLETE / BLOCKED upon conclusion of Phase 4A.

## 2. Verified Identity → Inventory Authentication Flow
**Evidence Source:** `AaramIdentity/backend/app/auth/service.py` (`create_service_token`) & `Aaram_Inventory/src/foundation/authentication/dependencies.py` (`get_current_user`)

* **Request:** Brain Core calls `POST /auth/service-token` (or `/service-accounts`) on AaramIdentity using its client credentials.
* **JWT Contract:** The issued RS256 token contains:
  * `sub`: `sa:<client_id>`
  * `type`: `service`
  * `roles`: (Least-privilege candidate; not definitively established by repository evidence yet)
  * `applications`: E.g., `["AARAM_INVENTORY"]`
* **Inventory Verification:** AaramInventory's `get_current_user` natively accepts this structure. It catches the invalid `uuid.UUID` parsing of the `sa:` prefix and safely wraps it in a deterministic `uuid5`. No modifications to AaramInventory are needed to support these tokens.

## 3. Verified Inventory API Contract
**Evidence Source:** `Aaram_Inventory/src/api/v1/read_api_router.py`

* **Endpoint:** `GET /read/inventory/balance`
* **HTTP Method:** `GET`
* **Parameters:** `warehouse_id` (UUID), `sku_id` (UUID)
* **Response Fields:** `{"warehouse_id": "...", "sku_id": "...", "balance": <int|Decimal>}`

## 4. Brain Mapping
**Flow:**
1. ShopDeck-derived `SKU ID` is passed to the adapter.
2. Adapter queries AaramInventory to retrieve the single active `warehouse_id`.
3. Adapter executes: `GET /read/inventory/balance?warehouse_id=...&sku_id=...`
4. Adapter extracts the `balance` field.
5. `balance` is mapped strictly to Brain's `InventoryContext.quantity_on_hand`.
6. Boolean availability is derived if required downstream (e.g. `quantity_on_hand > 0`).

* **Confirmations:**
  * `confidence_score` is NOT present in this endpoint's payload, confirming it is entirely ignored and not required by Brain.
  * No AaramPacking dependency exists in this flow.

## 5. Authentication/Authorization Analysis
**Evidence Source:** `Aaram_Inventory/src/api/v1/read_api_router.py` (L16-23)

* **Finding (PUBLIC ENDPOINT):** The `GET /read/inventory/balance` endpoint is currently **PUBLIC**. It entirely lacks the `Depends(get_current_user)` or `Depends(require_permission)` decorators.
* **Security Distinction:** Service authentication exists for Brain → Inventory. AaramIdentity authenticates/identifies Brain as a service. However, AaramInventory's current `GET /read/inventory/balance` endpoint is PUBLIC and does not currently enforce an authentication or permission dependency.
* **Enforcement Reality:** Therefore, M2M provides legitimate service identity for the request, but the current balance endpoint does not currently enforce that identity. Do NOT claim that M2M authorization protects the balance endpoint.
* **Future-Proofing:** Do NOT modify AaramInventory. Brain does NOT require `AARAM_INVENTORY_ADMIN` or `AARAM_BOOKS_ADMIN`. Do not invent a definitive read-only permission if repository evidence does not establish one.

## 6. Exact Phase 4A File Boundary
According to `docs/10-implementation-plan/implementation-backlog.md`:
* **Allowed to Create:** `src/business_adapters/inventory/*.py`, `tests/business_adapters/inventory/test_adapter.py`
* **Allowed to Modify:** `requirements.txt`
* **Must Remain Untouched:** AaramInventory, AaramIdentity, AaramPacking, ShopDeck, Brain Core logic.

## 7. Exact Implementation Tasks
1. Build `InventoryProvider` inside `src/business_adapters/inventory/`.
2. Implement dynamic `warehouse_id` retrieval from AaramInventory.
3. Implement `GET` call to the Inventory balance API.
4. Pass Bearer token (even though the endpoint is public, we implement the M2M contract as designed).
5. Parse `balance` and map to `quantity_on_hand`.
6. Return the populated `InventoryContext`.

## 8. Exact Test Requirements
Tests (using deterministic mocks/wiremock, not production credentials) must prove:
* Correct `sku_id` is passed.
* Correct warehouse resolution flow (including 0 or >1 warehouse failure states).
* Correct endpoint is targeted for balance.
* Successful extraction and mapping of `balance` to `quantity_on_hand` (zero and positive).
* `confidence_score` is completely ignored (even if mocked into the response).
* AaramPacking is not referenced.
* Network/HTTP errors propagate correctly to the caller.
* Authentication setup is structurally correct (Bearer header present).

## 9. ShopDeck Blocker
**SHOPDECK = BLOCKED**
* **Reason:** No legitimate headless/server-to-server ShopDeck connectivity is currently available. The existing ShopDeck MCP requires an interactive OTP/session authentication flow (3-legged). Brain Core operates as a background intelligence daemon and cannot satisfy interactive prompts.
* **Constraint:** We must not invent an API token, OAuth flow, or headless MCP mechanism. The dependency remains firmly external.

## 10. AaramPacking Exclusion
* AaramPacking is permanently **OUT OF SCOPE** as a Context Provider. It is a physical execution boundary. No adapter will be created.

## 11. Remaining Risks/Questions
None. File permissions have been granted.

## 12. Phase 4A Exit Criteria
1. The Inventory Context Adapter codebase is complete.
2. Unit/Mock tests satisfy all conditions listed in Section 8.
3. Overall Phase 4 status is formally updated to "PARTIALLY COMPLETE / BLOCKED" (awaiting ShopDeck headless access).

## 13. FINAL OPEN QUESTIONS — OWNER REVIEW

### 1. Warehouse ID Determination
* **Status:** `WAREHOUSE_ID_STATUS = RESOLVED`
* **Decision:** AaramInventory owns warehouse identity. The current system is single-warehouse. Brain obtains the warehouse ID from AaramInventory rather than hardcoding or deriving it from ShopDeck. (If 0 warehouses are found, fail explicitly. If >1 are found, fail/report unsupported multi-warehouse explicitly).

### 2. ProviderRegistry Modification Determination
* **Status:** ProviderRegistry modification is NOT required.
* **Decision:** The existing registry API exposes a dynamic `register()` method. The adapter can be registered dynamically at runtime from the composition root without violating open-closed principles.

## 14. Final Phase 4A Readiness Summary
1. **Exact Inventory authentication flow:** Brain fetches an RS256 JWT from AaramIdentity `POST /auth/service-token` using M2M client credentials and passes it as a Bearer token to AaramInventory.
2. **Exact warehouse ID acquisition flow:** Brain queries AaramInventory for the list of warehouses. If `count == 1`, it extracts the `warehouse_id`. If `count == 0` or `count > 1`, the adapter fails explicitly.
3. **Exact SKU ID acquisition assumption:** The SKU ID is resolved from ShopDeck prior to invoking the Inventory Context Adapter.
4. **Exact balance query:** `GET /read/inventory/balance?warehouse_id=<uuid>&sku_id=<uuid>` on AaramInventory.
5. **Exact quantity_on_hand mapping:** The `balance` field in the response is mapped directly to `InventoryContext.quantity_on_hand`.
6. **Confirmation that confidence_score is ignored:** Confirmed. The target API does not return it, and Brain will strictly ignore it even if it did.
7. **Confirmation that AaramPacking is excluded:** Confirmed. AaramPacking is not part of Context.
8. **ShopDeck headless connectivity remains blocked:** Confirmed. ShopDeck integration cannot proceed without headless auth.
9. **Exact source files allowed for Phase 4A:** `src/business_adapters/inventory/*.py`, `tests/business_adapters/inventory/test_adapter.py`, `requirements.txt`.
10. **Exact test files required:** `tests/business_adapters/inventory/test_adapter.py`.
11. **Exact remaining governance gaps:** None. Explicit permission was granted.
