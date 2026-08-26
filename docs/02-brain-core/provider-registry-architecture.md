# Provider Registry Architecture

## 1. Purpose
The Provider Registry solves the problem of dynamic resolution for Business Adapters. It provides the mechanism for the Context Engine to look up and invoke the correct concrete adapter at runtime based on the `SourceSystem` and the required capability.

## 2. Ownership
- **Registry Interface:** Belongs entirely to Brain Core (`context_engine/registry.py`).
- **Capability Definition:** Belongs entirely to Shared Context Contracts (`shared/context_contracts/capability.py`). The registry remains generic infrastructure and does not own the business capability enum.
- **Registration / Wiring:** The application composition root (`main.py`) is responsible for registering concrete providers into the registry. (See: [Application Composition Boundary](../01-architecture/application-composition-boundary.md)).
- **Dependency Isolation:** Brain Core must **never** import concrete business adapters directly.

## 3. Registration Key
Providers are registered and resolved using a composite key:
`(SourceSystem, Capability)`

## 4. Registration Rule
- There can be **exactly one** provider per `(SourceSystem, Capability)`.
- If an attempt is made to register a duplicate provider for an existing key, the registry must fail immediately by raising a `DuplicateProviderRegistrationError` during application startup.

## 5. Resolution Rule
- If the Context Engine requests a provider for a specific `(SourceSystem, Capability)` and it does not exist, the registry must fail immediately by raising a `ProviderNotRegisteredError`.
- The engine must **never** silently return incomplete context. If a requested source is missing its provider, it is a critical failure.

## 6. Dependency Direction

```text
   Business Adapter Implementation
             ↑
       Provider Contract
             ↑
       Provider Registry
             ↑
       ContextAssembler

   Application Composition Root
             |
             └── registers concrete providers
```

## 7. Dynamic Resolution Rationale
Dynamic resolution is strictly required because multiple independent systems can provide the exact same capability. For example, `CustomerContext` could be sourced from:
- ShopDeck
- Amazon
- Flipkart
- Future third-party marketplaces

By relying on dynamic resolution via the Provider Registry, Brain Core remains agnostic to these platforms, allowing safe and seamless extension of AaramBooks capabilities.
