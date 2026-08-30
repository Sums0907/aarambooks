# Context Capability Matrix (Stage F)

This matrix tracks the generic, reusable business capability boundaries that Brain Core can invoke to fetch context. Missing capabilities represent **Context Capability Gaps** to be prioritized in future Business System CEM implementations.

| Capability URN | Purpose | Authoritative Business System | Context Exposure Mechanism | Generic Protocol Active? | Gap Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`urn:aaram:capability:customer:profile`** | Demographics, identity, lifetime value. | Customer/ShopDeck | CEM Endpoint | No (Legacy Model used) | Partially Resolved |
| **`urn:aaram:capability:order:state`** | Order items, total, status, history. | ShopDeck | CEM Endpoint | No (Legacy Model used) | Partially Resolved |
| **`urn:aaram:capability:inventory:availability`** | Physical stock balance on hand. | AaramInventory | AaramInventory CEM | Yes | Active |
| **`urn:aaram:capability:inventory:catalog`** | Dimensions, weight, UoM, pricing, BOM. | AaramInventory | AaramInventory CEM | Pending Implementation | **GAP** |
| **`urn:aaram:capability:fulfillment:tracking`** | Delivery status, attempts, carrier. | Shiprocket | Shiprocket CEM / Webhooks | No (Legacy Model used) | Partially Resolved |
| **`urn:aaram:capability:inventory:movements`** | Historical ledger of ins and outs (dispatch). | AaramInventory | AaramInventory CEM | Pending Implementation | **GAP** |
| **`urn:aaram:capability:inventory:exceptions`** | Discrepancies, cycle count variances. | AaramInventory | AaramInventory CEM | Pending Implementation | **GAP** |
| **`urn:aaram:capability:inventory:jobwork`** | Raw material issues, FG receipts, scrap. | AaramInventory | AaramInventory CEM | Pending Implementation | **GAP** |

*Note: Context Capability Gaps are not Intelligence Domain failures. They denote areas where the external Business Systems must implement new CEM endpoints to expand Brain Core's understanding.*
