# ADR-006: AaramIdentity M2M Authentication

**Status:** APPROVED
**Date:** 2026-08-26

## Context
Aaram Brain Core (a headless backend service) needs to securely communicate with internal operational systems like AaramInventory to retrieve operational context (e.g., `quantity_on_hand`).
Currently, AaramIdentity only issues JSON Web Tokens (JWTs) via interactive human login flows (Password or Phone/PIN). There is no native mechanism for an internal backend service to authenticate itself.

## Architectural Decision
1. **AaramIdentity remains the Central Authentication Authority:** All backend-to-backend authentication within the Aaram ecosystem must be mediated by AaramIdentity to maintain a single source of trust and auditing.
2. **Implement Machine-to-Machine (M2M) Identity:** AaramIdentity must support a Service Account (or Client Credentials) capability that can issue valid RS256 Bearer JWTs to trusted internal services (like Brain Core) using a high-entropy secret, rather than a human password.
3. **Reject Human JWT Impersonation:** Brain Core must NOT use a hardcoded human user account or intercept human OTPs/passwords to fake its identity.
4. **Reject Static Downstream API Keys:** AaramInventory must NOT be modified to accept static, unexpiring API keys or separate middleware bypassing AaramIdentity.

## Implementation Status
The corresponding AaramIdentity M2M capability has been implemented and tested in its separate workspace. 

The implementation/audit evidence includes:
- `ServiceAccount` model
- `POST /auth/service-token` endpoint
- Short-lived RS256 service JWT
- `sub = sa:<client_id>`
- `type = service`
- `roles`/`applications` claims
- bcrypt-hashed client secrets
- Plaintext secret returned only once at creation
- Rate limiting on service-token authentication
- Automated M2M tests
- Compatibility with AaramInventory's existing JWT validation

*(Note: Production deployment is not claimed unless future source material proves it.)*

## Consequences
- **Positive:** Preserves the zero-trust architecture and centralizes identity management.
- **Positive:** AaramInventory's existing JWT validation logic natively accepts AaramIdentity-signed RS256 JWTs. Brain Core's service token will be structurally identical and will not require code changes in AaramInventory.
- **Security:** High-entropy service secrets must be securely injected into Brain Core's environment.
