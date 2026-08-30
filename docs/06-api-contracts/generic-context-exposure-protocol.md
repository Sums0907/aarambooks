# Generic Context Exposure Protocol — Design & Implementation Strategy

This document defines the generic protocol/socket between Brain Core and ANY external Business System Context Exposure Module (CEM). It is universally applicable to any business system (Inventory, NDR, Customer Query, Shopify, Shiprocket, etc.) and is strictly agnostic to domain-specific URNs, APIs, or business rules.

## 1. Architectural Boundaries

According to the Stage F Generic Context Capability Framework:
- **Brain Core** owns Cognitive Planning. It parses intent and produces generic semantic requirements (`ResolvedSemanticRequirement`). It does not know how to fulfill them.
- **Business Systems** (e.g., Inventory, NDR) own their physical reality. They independently determine their capability boundaries, internal execution strategies, and how to translate generic semantics into their physical databases/APIs.
- **Context Exposure Module (CEM)** is the component built *within* the Business System workspace. It exposes an HTTP/gRPC endpoint that adheres to this generic protocol, allowing Brain Core to query it.

## 2. Generic Context Capability Request Contract

When Brain Core needs context, the `ContextCapabilityGateway` transmits a request to the appropriate CEM. The payload is strictly generic.

### HTTP/REST Protocol Example
`POST /api/internal/brain/invoke-capability`

```json
{
  "request_id": "req-12345",
  "capability_urn": "urn:aaram:capability:business_system:feature",
  "authorization_context": {
    "token": "m2m-token-string",
    "roles": ["brain_core"]
  },
  "semantic_requirement": {
    "identity": "some_business_entity",
    "constraints": [
      {
        "identity": "some_business_entity.attribute",
        "operator": "EQUALS",
        "bound_value": "value123"
      }
    ]
  }
}
```

## 3. Generic Context Capability Response Contract

The Business System's CEM parses the request, executes its own proprietary logic, and returns a generic response containing an opaque payload (`EvidenceItem`).

### Response Payload
```json
{
  "request_id": "req-12345",
  "status": "SUCCESS",
  "capability_urn": "urn:aaram:capability:business_system:feature",
  "evidence": [
    {
      "source_urn": "urn:aaram:source:business_system",
      "retrieved_at": "2026-08-28T12:00:00Z",
      "data_payload": {
         // OPAQUE JSON: Brain does not parse this schema.
         // It is passed directly to the LLM Context Window.
         "internal_field_1": "value",
         "internal_field_2": 42
      }
    }
  ],
  "gap_semantics": []
}
```

## 4. Capability Registration & Discovery
- Business Systems must register their exposed Capabilities (URNs) and the corresponding CEM Endpoint URL with Brain Core's **Provider Registry** via configuration or startup registration.
- Brain Core routes requests strictly by matching the semantic requirement to the registered Capability URNs.

## 5. Implementation Boundary

### BRAIN WORKSPACE (`aarambooks`):
- Provides the `ContextCapabilityGateway` (generic transport client).
- **Scope:** Receives endpoint configuration, marshals the `ResolvedSemanticRequirement` into JSON, fires it via HTTP POST, and unmarshals the generic response. No domain-specific logic allowed.

### BUSINESS SYSTEM WORKSPACE (e.g., `aaraminventory`):
- Implements the Context Exposure Module (CEM).
- **Scope:** Receives the generic HTTP invocation, parses the `SemanticConstraints`, translates them into internal DB/API queries (handling operations like aggregations natively), and returns the authoritative JSON `data_payload`, maintaining sole ownership of the physical evidence schema.

## 6. Security & M2M Connectivity
All interactions between Brain Core and a Business System CEM must utilize Machine-to-Machine (M2M) authentication tokens (e.g., JWT) validated at the CEM boundary to ensure zero-trust security across microservices.
