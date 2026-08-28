# Inventory Intelligence: Context Capability Mapping

## Purpose
This document maps how the `inventory-intelligence` domain translates natural-language inventory questions into abstract **Context Capability Requests** handled by Brain Core, ensuring complete decoupling from AaramInventory APIs.

## The Abstraction Contract
When an inventory question is asked, the domain parses the intent and constructs a `ContextAssemblyRequest`. It never makes an HTTP call to AaramInventory.

```python
# Example Domain Logic
request = ContextAssemblyRequest(
    source_system=SourceSystem.aaram_inventory,
    capabilities=[ProviderCapability.INVENTORY_AVAILABILITY, ProviderCapability.JOBWORK_CONTEXT],
    identifiers={"sku_id": "SKU-999"}
)
# The domain yields this request to Brain Core, and awaits the AssembledContext.
```

## Mapping Evaluation Scenarios to Capabilities

Below is how the domain logically maps the 17 evaluation scenarios into generic Context Capability requests.

### 1. Exception Analysis & Diagnostics
- **Target Intelligence:** Understanding why physical stock deviates from ledger stock.
- **Capabilities Required:** `INVENTORY_EXCEPTIONS`, `INVENTORY_MOVEMENTS`, `SKU_CONTEXT`.
- **Domain Reasoning:** Correlate dates of negative exceptions with unbilled dispatch movements.

### 2. Third-Party Jobwork & Material Leakage
- **Target Intelligence:** Tracking raw materials issued to vendors vs finished goods received.
- **Capabilities Required:** `JOBWORK_CONTEXT`, `INVENTORY_LEDGER`, `SKU_CONTEXT`.
- **Domain Reasoning:** Deterministically subtract Receipts from Issues to calculate Yield and Pending stock.

### 3. Availability & Production Readiness
- **Target Intelligence:** Deciding if an order can be fulfilled immediately or if assembly is required.
- **Capabilities Required:** `INVENTORY_AVAILABILITY`, `SKU_CONTEXT` (specifically BOM), `JOBWORK_CONTEXT`.
- **Domain Reasoning:** If FG balance < required, traverse BOM context to verify RM balances.

### 4. Aggregation, Ranking, and Factual Lookup
- **Target Intelligence:** Identifying top performers and master data gaps.
- **Capabilities Required:** `INVENTORY_MOVEMENTS`, `SKU_CONTEXT`.
- **Domain Reasoning:** Sum quantity in Sales movements over a time window. Sort desc.

### 5. Financial Reconciliation & Ledger Anomaly Detection
- **Target Intelligence:** Ensuring physical movements match financial journals.
- **Capabilities Required:** `INVENTORY_LEDGER`, `INVENTORY_MOVEMENTS`, `JOBWORK_CONTEXT`.
- **Domain Reasoning:** Cross-reference movement reference IDs against journal entry IDs. Flag orphans.

## Handling Gaps
If `ContextAssembler` returns a `ProviderNotRegisteredError` for `ProviderCapability.JOBWORK_CONTEXT`, the domain catches the error and outputs:
*"I cannot analyze third-party jobworker leakage because the Jobwork context capability is currently unavailable in the ecosystem."*
It does NOT attempt a fallback API call.
