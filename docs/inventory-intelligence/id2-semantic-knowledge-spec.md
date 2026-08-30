# Inventory Semantic Knowledge Specification (ID-2)

## 1. Objective
This document formally establishes the Semantic Knowledge specification for the Inventory Intelligence Domain. ID-2 will implement this specification by expanding `src/intelligence_domains/inventory_intelligence/knowledge.py` to seed and query the `AzmProvider` with these exact concepts, policies, and capability mappings.

This knowledge bridges the gap between natural language user intents and Brain Core's strict `EvidenceRequirement` structures.

---

## 2. Domain Vocabulary & Semantic Concepts
The `AzmProvider` must be populated with the following inventory-specific `SemanticConcept` definitions to allow the LLM gateway (in the Semantic Requirements Engine) to translate ambiguous human terms into known ecosystem entities.

### Core Entities
| Semantic Concept | Description | Maps to Entity Type |
| :--- | :--- | :--- |
| **SKU** | A unique stock-keeping unit representing a physical product. | `inventory.entity.sku` |
| **Warehouse** | A physical location owned by Aaram where goods are stored. | `inventory.entity.warehouse` |
| **Jobworker / Vendor** | A third-party partner who holds Aaram raw materials for assembly. | `inventory.entity.jobwork_vendor` |
| **Movement** | Any ledger entry representing the flow of stock in or out. | `inventory.entity.posting_date` |

### Derived Business Concepts
| Semantic Concept | Definition / LLM Translation Rule |
| :--- | :--- |
| **Low Stock** | Indicates a request for `INVENTORY_AVAILABILITY` filtered where physical balance falls below the established Reorder Threshold. |
| **Pending Return** | Indicates a request for `JOBWORK_CONTEXT` where Raw Material Issue qty > Finished Goods Receipt qty. |
| **Leakage / Wastage** | Indicates a request for `JOBWORK_CONTEXT` specifically tracking the Scrap metric. |
| **Exception / Discrepancy**| Indicates a request for `INVENTORY_EXCEPTIONS` where physical counts differ from ledger counts. |
| **Valuation / COGS** | Indicates a request for `INVENTORY_LEDGER` focusing on financial unit cost multiplied by dispatch quantity. |

---

## 3. Standard Operating Procedures (SOPs)
During the REASONING phase of the DomainCase lifecycle, the ID Orchestrator must dynamically inject relevant SOPs into the LLM `system_prompt` based on the intent. These are the SOPs that ID-2 will formalize in Azm:

### SOP: Negative Stock Policy
**Trigger Intent:** Exceptions, negative balances.
**Rule:** "AaramBooks does not allow negative physical stock. If the `INVENTORY_EXCEPTIONS` capability shows a negative balance, it must be flagged as a 'High Severity System Discrepancy'. Do not recommend fulfilling orders against negative stock. Recommend triggering an immediate cycle count."

### SOP: Reorder Threshold Policy
**Trigger Intent:** Low stock, availability, replenishment.
**Rule:** "A SKU is considered 'Low Stock' if its available physical balance drops below its defined Reorder Point (or below 14 days of average trailing dispatch volume). If low stock is detected, output a `RecommendReorder` decision."

### SOP: Jobwork Aging Policy
**Trigger Intent:** Jobwork status, vendor tracking.
**Rule:** "Raw materials sitting at a Jobworker location for > 30 days without yielding Finished Goods are considered 'At Risk'. You must highlight vendors with At Risk materials and suggest a Vendor Audit action."

---

## 4. Semantic Capability Mapping Matrix
To allow the ID's Semantic Requirements Engine to construct valid `ContextAssemblyRequest`s, it needs to know which capabilities answer which semantic concepts. ID-2 will codify this matrix into the domain knowledge:

| User Intent Theme | Required Brain Core Capability URN | Required Constraints |
| :--- | :--- | :--- |
| "What is the stock of..." | `urn:aarambooks:inventory:capability:balance` | `sku` |
| "Show me movements for..."| `urn:aarambooks:inventory:capability:ledger` | `sku`, `posting_date` |
| "What is pending with Vendor X"| `urn:aarambooks:inventory:capability:jobwork_status` | `jobwork_vendor` |
| "Why is the stock negative?" | `urn:aarambooks:inventory:capability:exception_status`| `sku` |

---

## 5. Execution Strategy for ID-2
When ID-2 begins, the implementation will strictly adhere to:
1. **No Hardcoding:** The tables in Section 2 and 3 will be serialized into the PostgreSQL `AzmProvider` (via `PgVectorKnowledgeAdapter`), NOT hardcoded into `orchestrator.py`.
2. **Knowledge Retrieval:** `InventorySemanticKnowledge` will be updated to fetch both Concepts (for Intent Parsing) and SOPs (for Reasoning).
3. **Prompt Injection:** The `REASONING` state in the ID Orchestrator will be modified to append retrieved SOPs into the `GatewayGenerationRequest` system prompt, explicitly grounding the model's output in Aaram's business policies.
