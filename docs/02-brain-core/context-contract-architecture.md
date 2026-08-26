# Shared Context Contracts Architecture

## Purpose
The Shared Context Contracts establish the standardized data models exchanged between Business Adapters and the Brain Core Context Engine. 

By extracting these contracts into a standalone `shared` module, we enforce a clean boundary where neither the Context Engine nor the Business Adapters own the definition of the communication protocol.

## Dependency Direction
The dependency flow intentionally points inward toward the shared contracts:

```text
          Shared Context Contracts
              ↑              ↑
      Business Adapters   Brain Core
```

## Contents of Shared Contracts
Shared contracts strictly contain data models (schemas) and enumerations:
- `CustomerContext`
- `OrderContext`
- `InventoryContext`
- `FulfillmentContext`
- `SourceSystem` (enum)
- `ProviderCapability` (enum)
- `ContextSource` (provenance metadata)

## Constraints
What must **not** exist in shared context contracts:
- Business logic or algorithms.
- API clients or HTTP handlers.
- Database access or ORM models.
- Adapter implementations.
