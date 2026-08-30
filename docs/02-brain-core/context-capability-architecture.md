# Context Capability Architecture (Stage F Generic Protocol)

## 1. Purpose

This document defines the **Generic Context Capability Model**, the architectural mechanism through which Brain Core requests and receives business truth from external Business Systems (e.g., AaramInventory, Shiprocket) without owning physical schemas or knowing how that truth is physically obtained.

## 2. Terminology

- **Business Truth:** Authoritative operational data owned entirely by external Business Systems. Brain Core never owns this data.
- **Context Capability (URN):** A logical, generic identifier (e.g., `urn:aaram:capability:inventory:availability`) that Brain Core uses to request business truth.
- **Semantic Constraint:** A source-blind definition of what is needed (e.g., "Give me entity X where attribute Y equals Z").
- **EvidenceItem:** An opaque JSON payload returned by a Business System. Brain Core does NOT parse the schema of this payload; it merely injects it into the LLM context.
- **Context Exposure Module (CEM):** The component built *inside* the Business System workspace that exposes capabilities to Brain Core via a generic HTTP/gRPC socket.
- **Provider Registry:** Brain Core's internal registry mapping Capability URNs to Business System CEM endpoints.

## 3. Boundaries

```text
+------------------------+      Declares Semantic      +-----------------------+
|  Intelligence Domain   | --------------------------> | Brain Core Context    |
|  (Reasoning & Intent)  |       Requirement           | Layer                 |
+------------------------+                             +-----------------------+
           ^                                                  |
           |                                                  | Generic HTTP
           |                                                  | Capability Req
           |                                                  v
           |                                           +-----------------------+
           |                                           | Context Exposure Mod  |
           +----- Injects Opaque EvidenceItem -------- | (Business System)     |
                                                       +-----------------------+
```

## 4. Capability Model and Request Abstraction

Brain Core must NOT request explicit APIs (e.g., `GET /api/v1/inventory`).
Instead, the Intelligence Domain issues a `SemanticRequirement` bound to a specific Context Capability URN. 

The `ContextCapabilityGateway` transmits a strictly generic payload to the Business System CEM:
- `CapabilityURN`
- `ResolvedSemanticRequirement`
- `Authorization Context`

## 5. Generic Responses (Source Blindness)

The Business System CEM translates the semantic requirement into its internal database queries, and returns an `EvidenceItem` containing a `data_payload` (opaque JSON) and `source_urn`. 

Brain Core does not deserialize the `data_payload` into a Pydantic schema like `InventoryContext`. It remains completely unaware of physical fields.

## 6. Context Resolution Semantics

- **Available Truth:** The CEM successfully retrieved the capability and returned an `EvidenceItem`.
- **Unavailable Truth:** The underlying CEM is unreachable (e.g., HTTP 503).
- **Context Capability Gap:** If the `ProviderRegistry` has no registered endpoint for the requested Capability URN, it raises a `ProviderNotRegisteredError`.

## 7. Preventing Hallucination

The opaque `data_payload` inside the `EvidenceItem` is injected verbatim into the LLM context window, alongside its provenance (`source_urn`). The LLM prompt explicitly instructs the reasoning engine to only extract facts from the provided JSON evidence, eliminating hallucination while decoupling Brain Core from physical schema changes.
