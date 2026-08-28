# Context Capability Matrix

This matrix tracks the generic, reusable business contexts that Brain Core's Context Layer can provide to Intelligence Domains. Missing contexts represent **Context Capability Gaps** to be prioritized in future adapter iterations.

| Context Capability | Purpose | Source System | Current Brain Core Resolution Mechanism | Normalized Context Exists? | Gap Status | Generic / Reusable? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Customer Profile** | Demographics, identity, lifetime value. | ShopDeck | `ShopDeckAdapter` | Yes (`CustomerContext`) | Resolved | Yes |
| **Order State** | Order items, total, status, history. | ShopDeck | `ShopDeckAdapter` | Yes (`OrderContext`) | Resolved | Yes |
| **Warehouse Context** | Location metadata, active status. | AaramInventory | `AaramInventoryAdapter` | Partially (ID extraction) | Partially Available | Yes |
| **SKU/Catalog Context** | Dimensions, weight, UoM, pricing, BOM structure. | AaramInventory | `AaramInventoryAdapter` | Yes (`InventoryContext` subset) | Partially Available (Missing BOM) | Yes |
| **Inventory Availability** | Physical stock balance on hand. | AaramInventory | `AaramInventoryAdapter` | Yes (`InventoryContext`) | Resolved | Yes |
| **Shipment Tracking** | Delivery status, attempts, carrier. | Shiprocket / ShopDeck | `ShiprocketAdapter` | Yes (`ShipmentContext`) | Resolved | Yes |
| **Inventory Movements** | Historical ledger of ins and outs (dispatch, receipts). | AaramInventory | None | No | **GAP** | Yes |
| **Inventory Exceptions** | Discrepancies, cycle count variances. | AaramInventory | None | No | **GAP** | Yes |
| **Jobwork Context** | Raw material issues, FG receipts, pending third-party stock, scrap. | AaramInventory | None | No | **GAP** | Yes |
| **Production Readiness** | Computed availability of required BOM components against stock. | AaramInventory | None | No | **GAP** | Yes |
| **Inventory Ledger** | Accounting journals, asset valuation, COGS. | AaramInventory | None | No | **GAP** | Yes |

*Note: Context Capability Gaps are not Intelligence Domain failures. They denote areas where the Context Layer must implement new providers/endpoints to expand Brain Core's understanding.*
