# Context Engine (Stage F Generic Architecture)

## 1. Purpose

The Context Engine is a core capability of Aaram Brain Core responsible for aggregating business truth using a generic, source-blind capability framework.

Its purpose is to provide the necessary operational context required for meaningful intelligence without owning or defining physical data schemas.

> Business systems create truth. Aaram Brain fetches that truth via generic capabilities and injects it into reasoning workflows.

---

## 2. Core Responsibility

The Context Engine leverages the **ContextCapabilityGateway** to dynamically route generic semantic requests (`ResolvedSemanticRequirement`) to registered Context Exposure Modules (CEMs) hosted by external Business Systems.

The Context Engine does not know what physical fields exist (e.g., `quantity_on_hand`, `awb_number`). It only knows about capability URNs (e.g., `urn:aaram:capability:inventory:availability`).

---

## 3. Relationship With Business Systems

Business systems remain the complete owners of operational truth and physical schemas.

Example Interaction:

```text
Brain Core
- Requires capability `urn:aaram:capability:inventory`
- Emits SemanticConstraint (identity: SKU, operator: EQUALS, value: 123)

        | (Generic HTTP POST via ContextCapabilityGateway)
        v

AaramInventory CEM (Context Exposure Module)
- Receives SemanticConstraint
- Translates to native SQL query
- Returns generic ContextCapabilityResult with opaque JSON evidence

        |
        v

Brain Core
- Receives opaque JSON evidence
- Injects JSON verbatim into LLM Context Window
```

The Context Engine never parses the JSON payload into rigid Pydantic models.

---

## 4. Context Boundaries

The Context Engine must not:
- Create operational records.
- Change business states.
- Define physical domain schemas (e.g., `InventoryContext`).
- Know about specific API endpoints inherently (uses `ProviderRegistry` instead).

---

## 5. Legacy Transitional Dependencies

*Note on Phase 1 Legacy Models:* During the Stage F.1 architectural transition, models such as `CustomerContext`, `OrderContext`, `ShipmentContext`, and `DeliveryAttempt` remain temporarily as legacy transitional dependencies strictly to support Event Bus and downstream Orchestrator workflows. They are explicitly isolated from the new Generic Context Capability Gateway.

---

## 6. Final Architecture Statement

The Context Engine is the situational understanding layer of Aaram Brain Core. It operates entirely through source-blind generic capability URNs and semantic constraints, preserving 100% of physical schema ownership within external business systems.
