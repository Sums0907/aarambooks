# M2M Connectivity Architecture Proposal

## 1. Current State
- **AaramIdentity** only issues RS256 Bearer JWTs to human `User` identities via interactive `/login` methods (Password/PIN). (VERIFIED)
- **AaramInventory** verifies RS256 JWTs by pulling AaramIdentity's public key. The `get_current_user` dependency requires the `AARAM_INVENTORY` application claim or an Admin role. It safely handles non-UUID subject claims by wrapping them in UUID5. (VERIFIED)
- **ShopDeck** currently only offers an interactive OTP-based MCP integration, which is incompatible with a headless service. (VERIFIED)

## 2. Problem
Brain Core (a headless intelligence orchestrator) cannot currently authenticate against AaramInventory or ShopDeck because it has no mechanism to legitimately acquire a non-human JWT or headless API credentials. 

## 3. Proposed AaramIdentity Service Identity Capability
To support Brain Core without breaking existing human authentication:
- **Service Identity Model:** Introduce a simple `ServiceAccount` or `Client` entity (e.g., `client_id`, `client_secret_hash`, `name`). (SUPPORTED)
- **Credential Difference:** Humans use Password/PIN; Services use a long, high-entropy generated API Secret (Client Credentials grant). (SUPPORTED)
- **Token Issuance Model:** A new dedicated endpoint (e.g., `POST /auth/token`) accepting `client_credentials`. (SUPPORTED)
- **Token Claims:** The issued JWT must perfectly mimic the human JWT structure expected by consumers:
  - `sub`: `client_id` (e.g., `brain-core-service`)
  - `roles`: `["SERVICE"]`
  - `applications`: `["AARAM_INVENTORY", "AARAM_PACKING"]`
  - `aud`: `"AARAM_ECOSYSTEM"`
- **Permission/PBAC Model:** Service Accounts should be explicitly granted the granular PBAC permissions required (e.g., `INVENTORY_READ_BALANCE`). (SUPPORTED)
- **Token Expiry:** Shorter lifespan (e.g., 15 minutes) with automated backend rotation, rather than long-lived refresh tokens. (SUPPORTED)

## 4. Brain Authentication Flow
1. Brain Core securely stores its `client_id` and `client_secret` in its environment.
2. On startup or token expiry, Brain calls `AaramIdentity` `POST /auth/token`.
3. Brain receives an RS256 Bearer JWT.
4. Brain injects `Authorization: Bearer <token>` into outbound requests to AaramInventory.
(SUPPORTED)

## 5. Brain → AaramInventory Authorization Flow
- **JWT Verification Compatibility:** The existing AaramInventory JWT verification **CAN** accept the proposed service token entirely unmodified. It only checks the signature and the `applications`/`roles` claims. Furthermore, its user extraction block safely handles non-UUID strings by wrapping them in UUID5, so `sub: "brain-core"` won't crash the dependency. (VERIFIED)
- **Authorization Changes Required:** Minimal to None. If the Brain token contains `AARAM_INVENTORY` in its `applications` list, it will pass the baseline `get_current_user` check. If specific read permissions are applied later, the token just needs them in the `permissions` list. (VERIFIED)
- **Field-Level Constraints (`quantity_on_hand` vs `confidence_score`):** The AaramInventory endpoint returns the full balance object. The existing AaramInventory authorization model **cannot** express field-level masking safely based on the token. Therefore, the enforcement must occur strictly at the Brain boundary (the AaramInventory Context Adapter must silently drop/ignore `confidence_score` during Pydantic deserialization). (VERIFIED)

## 6. ShopDeck Authentication Boundary
- **Headless Access:** UNKNOWN — ShopDeck-side technical contract/access required.
- **Intermediary Reuse:** UNKNOWN — No existing AaramBooks intermediary service was discovered that already authenticates with ShopDeck headlessly.

## 7. Security Model
- **Risks:** Service account secret leakage. Mitigated by strict environment injection and short JWT expiries.
- **Separation of Concerns:** Human routes (`/login`) remain completely untouched and independent of the M2M OAuth flow. (VERIFIED)

## 8. Backward Compatibility
- Zero impact on existing AaramIdentity human users. (VERIFIED)
- Zero impact on AaramInventory JWT verification (it is purely cryptographic and claim-based). (VERIFIED)

## 9. Exact Changes Eventually Required
1. **AaramIdentity:** Add `ServiceAccount` model. Add `POST /auth/token` route.
2. **Brain Core:** Add a token manager to fetch and attach the Bearer token.
3. **AaramInventory:** (Optional but recommended) Add explicit `Depends(require_permission("..."))` to the `/read/inventory/balance` endpoint if it's currently unprotected.

## 10. Systems That Would Need Modification
- AaramIdentity (to issue service tokens).

## 11. Systems That Must NOT Be Modified
- AaramInventory (existing JWT verification works as-is).
- Existing human authentication workflows.

## 12. Risks
- Delay in securing ShopDeck headless credentials prevents Context Engine assembly for orders/shipments.

## 13. Open Questions
- What is the exact ShopDeck headless API capability and credentialing mechanism?

## 14. Owner Decisions Required
- Approve the implementation of `ServiceAccount` (Client Credentials) in AaramIdentity.
- Provide the technical contract/credentials for ShopDeck backend connectivity.
