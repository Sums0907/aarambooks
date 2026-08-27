# Phase 4 Connectivity Reconciliation

## 1. Executive Conclusion
Phase 4 (Internal Operational Integrations) is **BLOCKED BY MISSING CAPABILITY**. AaramIdentity currently supports only interactive human users (via Password or Phone/PIN). There is zero implemented support for machine-to-machine authentication or service accounts. Consequently, Brain Core cannot legitimately obtain the JWT required to access AaramInventory's read APIs. Furthermore, ShopDeck headless backend connectivity remains unknown/missing. 

## 2. AaramIdentity Findings
A strict read-only inspection of the `AaramIdentity` backend confirms:
- **Supported Identities:** Only human `User` models are supported. (`app/models.py`)
- **Authentication Mechanisms:** Only `USERNAME_PASSWORD` and `PHONE_PIN` via `/login`. (`app/auth/router.py`)
- **Machine-to-Machine / Service Accounts:** **NOT IMPLEMENTED**. There are no `Client` or `ServiceAccount` entities.
- **Classification:** VERIFIED.

## 3. AaramInventory Findings
A strict read-only inspection of the `Aaram_Inventory` backend confirms:
- **Authentication Expectation:** AaramInventory expects an RS256 JWT issued by AaramIdentity, validated against Identity's public key (`/auth/public-key`).
- **Authorization Check:** The `get_current_user` dependency explicitly enforces that the token claims must contain `"AARAM_INVENTORY" in applications` or `"AARAM_BOOKS_ADMIN" / "AARAM_INVENTORY_ADMIN" in roles`. (`src/foundation/authentication/dependencies.py`)
- **Internal Service Callers:** The webhook endpoint for AaramPacking (`/internal/webhooks/packer/events`) is entirely unprotected (no `Depends` check), functioning on network trust. However, Brain Core needs read API access (e.g., `/read/inventory/balance`), which expects a legitimate Identity Context.
- **Classification:** VERIFIED.

## 4. ShopDeck Connectivity Findings
- **MCP Connectivity:** Interactive OTP (unsuitable for headless backend).
- **Backend/API Connectivity:** **UNKNOWN**. There is no existing AaramBooks server-side configuration, client library, or token mechanism for ShopDeck discovered in the inspected repositories.
- **Classification:** UNKNOWN — requires ShopDeck-side technical contract/access.

## 5. Brain → ShopDeck Connectivity Assessment
- **Protocol:** HTTP/REST (Assumed)
- **Authentication Mechanism:** Missing / Unknown
- **Required Identity:** Missing / Unknown
- **Available Today?:** No.
- **Evidence:** ShopDeck MCP requires OTP; no alternative headless token found in configuration.

## 6. Brain → AaramInventory Connectivity Assessment
- **Protocol:** HTTP/REST
- **Authentication Mechanism:** Bearer JWT (RS256)
- **Required Identity:** Requires a token with `AARAM_INVENTORY` application scope.
- **Available Today?:** No (Brain has no way to generate this JWT without impersonating a human).
- **Evidence:** `Aaram_Inventory/src/foundation/authentication/dependencies.py`

## 7. Existing Reusable Mechanisms
- **JWT Verification:** Yes. AaramInventory's `decode_aaramidentity_token` utility successfully pulls the public key from AaramIdentity to verify RS256 tokens locally without network roundtrips per request. This can be reused by Brain Core.

## 8. Missing Mechanisms
- **Service Accounts (AaramIdentity):** The ability to issue long-lived or machine-to-machine JWTs to trusted internal systems (like Brain Core) using Client Credentials.
- **ShopDeck API Credentials:** A headless API key or OAuth Client ID/Secret for ShopDeck.

## 9. Authentication/Security Requirements
- Brain Core MUST present a valid JWT to AaramInventory.
- Brain Core MUST NOT bypass AaramIdentity.
- Brain Core MUST NOT impersonate a human `User`.

## 10. Exact Evidence
- `AaramIdentity/backend/app/models.py` (No ServiceAccount models)
- `AaramIdentity/backend/app/auth/router.py` (Only human login methods)
- `Aaram_Inventory/src/foundation/authentication/dependencies.py` (Enforces token claims)
- `Aaram_Inventory/src/domains/inventory/api/packer_webhook_router.py` (Unprotected internal webhook)

## 11. Verification Matrix

| Conclusion | Classification |
|---|---|
| AaramIdentity only supports humans | VERIFIED |
| AaramInventory requires valid JWT | VERIFIED |
| AaramInventory packing webhook is unprotected | VERIFIED |
| ShopDeck headless credentials exist | UNKNOWN |
| Brain Core can authenticate today | CONTRADICTED |

## 12. Phase 4 Blocker Assessment
**BLOCKED BY MISSING CAPABILITY**
Phase 4 cannot proceed because Brain Core has no architectural or code-level mechanism to authenticate itself to AaramInventory or ShopDeck. 

## 13. Exact Owner Decisions Still Required
1. **Identity Strategy:** Will AaramIdentity be upgraded to support Service Accounts (Machine-to-Machine JWTs), or will a different backend-to-backend trust model be used?
2. **ShopDeck Headless Access:** What is the authoritative headless API/credential mechanism for ShopDeck?

## 14. Recommended Next Step
Do not write Phase 4 code. The Owner must direct the implementation of the Machine-to-Machine identity strategy (either upgrading `AaramIdentity` to issue service tokens, or providing explicit API keys).
