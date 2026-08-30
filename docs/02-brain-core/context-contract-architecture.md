# Shared Context Contracts Architecture (Stage F)

## Purpose
The Shared Context Contracts establish the standardized semantic protocol exchanged between external Business Adapters (CEMs) and the Brain Core Context Engine. 

By enforcing this boundary, Brain Core never owns physical domain schemas, and external systems only need to conform to generic semantic payloads.

## Dependency Direction
```text
          Generic Semantic Contracts
              ↑              ↑
      Business System CEM   Brain Core
```

## Contents of Shared Contracts
Shared contracts strictly contain abstract semantic routing mechanisms and generic capability declarations:
- `CapabilityURN` (Generic URNs identifying capabilities)
- `SemanticConstraint` (Source-blind query operators: identity, operator, bound_value)
- `ResolvedSemanticRequirement` (Aggregated constraints)
- `EvidenceItem` (Opaque JSON payload wrapper)
- `ContextCapabilityResult` (Generic HTTP response wrapper)
- `ContextCapabilityProvider` (Abstract protocol for capability fulfillment)
- `ContextCapabilityGateway` (Abstract HTTP transport client)

## Constraints
What must **not** exist in the new shared context contracts:
- Physical business schemas (e.g., `InventoryContext`, `ShipmentContext`).
- Business logic or algorithms.
- Domain-specific routing rules or endpoint definitions.

*(Note: Legacy Stage A-E execution models like `CustomerContext` and `ShipmentContext` reside strictly outside this generic protocol, functioning merely as temporary transitional structs for the Event Bus.)*
