# Phase 4 Independent Reconciliation Audit

## 1. Executive Status
CONTRACT_CONFLICT_REQUIRES_OWNER_DECISION

## 2. Evidence Sources
- Aaram_Ecosystem_Documentation_v1.0.md (via user uploads)
- AARAM_INVENTORY_INTEGRATION_CONTRACT.md (implied documentation)
- pakcerintegration_contract_report.md (implied documentation)
- Actual Source: `Sums0907/Aaram_Inventory` (cloned repository)
- Actual Source: `Sums0907/AaramPackerApp` (cloned repository)

## 3. Inventory Findings
AaramInventory acts as the ledger and master data source for the ecosystem.
- **Base URL:** `http://localhost:8100/api/v1` (locally) or `https://api.inventory.aarambooks.cloud/api/v1`
- **Auth:** HTTP Bearer token validated via AaramIdentity public key (RS256).
- **Core Endpoints:** `/read/inventory/balance` (GET), `/masters/products` (GET), `/masters/skus` (GET), `/masters/warehouses` (GET).
- **Responses:** Returns highly structured Pydantic models. Inventory balances return exact `quantity_on_hand` (float) and `confidence_score` (int), completely contradicting the simplistic `Dict[str, bool]` map defined in Brain Core's Phase 1 model.
- **Data Boundaries:** Fully owns products, SKUs, warehouses, and stock balances. Emits outbound stock projection events. Does NOT own order canonical state.

## 4. Packing Findings
AaramPacking executes warehouse workflows and owns order packing status.
- **Base URL:** Port `8000` or via `https://api.packing.aarambooks.cloud`
- **Auth:** HTTP Bearer token validated via AaramIdentity, scoped by strict PBAC (e.g. `PACKING_WORKFLOW_EXECUTE`, `PACKING_RTO_MANAGE`).
- **Core Endpoints:** `/orders/pending` (GET), `/orders/by-awb/{awb}` (GET), `/packer/labels/{awb}/pack` (POST), `/rto/lookup/{forward_awb}` (GET), `/queue` (GET for admin sync).
- **Responses:** Returns robust hierarchical orders arrays including granular items, AWB, and specific packing workflow statuses (`RECEIVED`, `PENDING_RECONCILIATION`, etc.).
- **Data Boundaries:** Owns packing execution events, labels, batches, and RTO receiving. Does NOT own financial tracking or inventory balances.

## 5. Source-Code Verification Matrix

| Claim | Master Documentation | Audit Report | Actual Source | Classification | Evidence |
|---|---|---|---|---|---|
| Inventory Balances is a boolean map | Brain Core Phase 1 | (implied) | Floats + Confidence Score | CONFLICT | `src/domains/inventory/schemas/balance.py` |
| Packing status is a single string | Brain Core Phase 1 | (implied) | Complex hierarchical order dicts | CONFLICT | `/orders/by-awb/{awb}` payload |
| Brain Core authenticates seamlessly | Brain Core Docs | (implied) | Requires Bearer Token with Identity permissions | BLOCKER | `auth/dependencies.py` enforces user roles. Machine-to-machine is unimplemented (Phase 2). |
| Brain Core owns business state | General assumption | (implied) | AaramInventory and AaramPacking own business state. | CORRECTED | Both repos define dedicated database tables for their domains. |

## 6. Exact Verified Inventory Contract
- **Protocol:** HTTP REST GET
- **Endpoints:** `/api/v1/read/inventory/balance`
- **Parameters:** `warehouse_id` (UUID), `sku_id` (UUID)
- **Response Schema:** 
  ```json
  {
    "warehouse_id": "<uuid>",
    "sku_id": "<uuid>",
    "quantity_on_hand": 10.0,
    "confidence_score": 100,
    "confidence_reasons": [],
    "last_movement_date": "2026-08-26T12:00:00Z"
  }
  ```

## 7. Exact Verified Packing Contract
- **Protocol:** HTTP REST GET
- **Endpoints:** `/orders/by-awb/{awb}`
- **Parameters:** `awb` (Path string)
- **Response Schema:**
  ```json
  {
    "order": {
        "status": "PACKED",
        "awb": "123456789",
        "items": [
           { "sku_code": "...", "quantity": 1 }
        ]
    },
    "items": [...]
  }
  ```

## 8. Brain Core Required Context
- **REQUIRED**: `quantity_on_hand` (Inventory), `confidence_score` (Inventory), Order `status` (Packing), `awb` (Packing).
- **OPTIONAL**: `warehouse_id`, `items` details.
- **EXCLUDED**: Internal database UUIDs, pagination meta, internal audit trails.

## 9. Authentication Contract
- **User JWT Capability**: Supported. `IdentityContext` decoded via `decode_aaramidentity_token()`.
- **Machine/Service Auth Capability**: **NOT SUPPORTED**. The Identity module states: *"Phase 2 will introduce Identity Service Accounts with dedicated SYSTEM_* permissions for webhook authentication."* Currently, no service account exists.
- **Blocker**: Yes. Brain Core (a background intelligence service) cannot natively authenticate to AaramInventory or AaramPacking without a valid User JWT or an established Service Account mechanism. Do not invent one.

## 10. Read vs Write Boundary
- **Brain Core May Consume (READ-ONLY):** `/read/inventory/balance`, `/orders/pending`, `/orders/history`, `/orders/by-awb/{awb}`, `/rto/lookup/{awb}`.
- **Brain Core MUST NOT Execute (WRITE):** `/packer/labels/{awb}/pack`, `/rto/scan`, `/staged/orders/{id}/confirm`, `/api/v1/skus` (POST/PATCH).

## 11. Discrepancies
1. **Schema Mismatch**: Phase 1 Context Contracts (`InventoryContext`, `FulfillmentContext`) heavily simplify reality. Inventory tracks exact numerical balances and confidence scores, not just `bool` availability maps.
2. **Auth Void**: Brain Core lacks a Service Account mechanism to query these external ecosystems without impersonating a human user or bypassing Identity.
3. **Event Polling**: Brain Core assumes synchronous state fetches, but AaramPacking/Inventory emit asynchronous events (Outbox patterns).

## 12. Owner Decisions Required
1. **Model Downcasting vs Evolution**: Should Phase 1 models be forcibly modified to accommodate the actual external Pydantic models (e.g. `confidence_score`), or should the adapters silently drop the rich data to comply with the frozen Phase 1 boolean schema?
2. **Authentication Strategy**: Since Phase 2 of Identity (Service Accounts) is not deployed, how should Brain Core authenticate its REST requests to these microservices?

## 13. Phase 4 Implementation Readiness
Adapter implementation is technically mapped, but fundamentally blocked by:
1. Missing Machine-to-Machine authentication capabilities.
2. Irreconcilable schema mismatches between the certified Phase 1 models and the actual external source codes.

## 14. Recommended Next Phase
Do NOT implement Phase 4 adapters yet. Escalate the identified discrepancies to the repository Owner to obtain an architectural ruling on Schema Evolution and Authentication strategy. Wait for Owner instructions.
