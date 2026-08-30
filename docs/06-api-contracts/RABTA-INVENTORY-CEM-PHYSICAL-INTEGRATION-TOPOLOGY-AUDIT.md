# RABTA ↔ Aaram Inventory CEM Physical Integration Topology Audit

**Date:** 2026-08-30
**Scope:** Read-only topology audit of AaramBrain (`rabta-baseline-certified`) and Aaram_Inventory (`aaram-inventory-cem-certified`).

---

## 1. Current Brain Topology (AaramBrain)
- **Environment:** Local development (via `docker-compose.yml` and `docker-compose.override.yml`).
- **Network:** Default docker-compose bridge network.
- **Exposed Ports:** `8000:8000` (API), `5432` (PostgreSQL), `4000` (LiteLLM).
- **Environment Configuration (`.env`):**
  - `PORT=8000`
  - `INVENTORY_URL=http://localhost:8100`
  - `BRAIN_CLIENT_ID=aaram_brain`

## 2. Current Inventory Topology (Aaram_Inventory)
- **Environment:** Local / Production-ready (via `docker-compose.prod.yml`).
- **Network:** Explicit `aarambooks_network` (bridge).
- **Exposed Ports:** `127.0.0.1:8100:8000` (API container listens on 8000, mapped to host's localhost 8100).
- **CEM API Endpoint:** `POST /api/v1/context/resolve`
- **Environment Configuration:**
  - `PORT=8000`
  - `IDENTITY_SERVICE_URL`
  - `AARAMIDENTITY_PUBLIC_KEY`

## 3. Exact CEM Endpoint URL
- The `ContextCapabilityGateway` currently attempts to call: `http://localhost:8100/api/v1/context/resolve` (derived from `INVENTORY_URL`).

## 4. Request/Response Contract Verification
- **Request:** `ContextCapabilityRequest` (JSON) containing `capability_urn` and `ResolvedSemanticRequirement`.
- **Response:** `ContextCapabilityResult` (JSON) containing `status`, `data` (dict), and `provenance_metadata`.
- Both schemas match the agreed Stage F Canonical Protocol.

## 5. Authentication Flow & Authorization Propagation
- **Token Propagation:** Brain Core blindly passes the `Authorization` header to Inventory.
- **App Identity:** Inventory CEM requires `"AARAM_BRAIN_APP"` in the JWT `applications` list.
- **Physical Permissions:** Mapped capability URNs enforce strict permissions (e.g., `INVENTORY_PRODUCT_VIEW`).

## 6. Tenant, User, and Session Propagation
- **Currently Existing:**
  - `tenant_id` and `user_id` are natively derived by Inventory CEM from the propagated JWT.
- **Not Wired/Required:**
  - `session_id` is managed strictly by Brain Core (R-10 Memory Continuity). It is intentionally excluded from the Stage F payload because CEM operations are stateless.

## 7. Network Path & Infrastructure Configuration Changes
- **Issue:** Brain's `INVENTORY_URL=http://localhost:8100` will fail when executing inside the Brain Docker container, as `localhost` points to the Brain container itself, not the host machine where Inventory is exposed.
- **Required Change for Local Testing:**
  - Change Brain's `.env` to `INVENTORY_URL=http://host.docker.internal:8100` OR place both containers on the same Docker network (e.g., `aarambooks_network`) and use `http://inventory-api:8000`.

## 8. Local Validation Plan
1. Start `Aaram_Inventory` using its `docker-compose.prod.yml` so it listens on `localhost:8100`.
2. Update AaramBrain `.env` to `INVENTORY_URL=http://host.docker.internal:8100`.
3. Start AaramBrain via docker-compose.
4. Execute an end-to-end intent (e.g., "Check balance for SKU X") and verify cross-container HTTP flow.

## 9. Production Network Path
- In production (VPS/Kubernetes), Brain must call the internal service DNS (e.g., `http://inventory-backend-svc:8000/api/v1/context/resolve`) rather than a localhost port mapping.

## 10. Relevant Configuration/Environment Variables
- **Brain (`aarambooks`):** `INVENTORY_URL`
- **Inventory (`Aaram_Inventory`):** `IDENTITY_SERVICE_URL`, `AARAMIDENTITY_PUBLIC_KEY`

## 11. CORS Considerations
- **Irrelevant.** The Brain ↔ Inventory CEM communication is strictly backend-to-backend. CORS policies do not apply.

## 12. TLS/HTTPS Requirements
- **Local:** HTTP over Docker bridge networks is sufficient.
- **Production:** If routing over an untrusted VPC or public internet, the connection must be upgraded to HTTPS. If routing inside a private Kubernetes cluster/Docker network, HTTP is standard, relying on TLS termination at the ingress.

## 13. Security Considerations & Blockers
- **Blockers:** None.
- **Security Check:** The Brain Core must successfully obtain or propagate a valid JWT with `AARAM_BRAIN_APP`. If it synthesizes requests asynchronously (e.g., background recommendations), it must securely acquire an M2M token rather than relying on an active user token.

## 14. Exact Implementation Sequence
1. Modify AaramBrain's `.env` to use Docker-resolvable hostnames (`host.docker.internal:8100`).
2. Boot Aaram Inventory using its certified Docker compose.
3. Boot AaramBrain.
4. Trigger an integration test that spans R-1 → R-8, traversing the actual network boundary.
