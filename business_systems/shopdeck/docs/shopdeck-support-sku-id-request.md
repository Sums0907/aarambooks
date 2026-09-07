**To:** ShopDeck Seller Support / Integrations Team  
**From:** Aaram Homes (Seller ID: 68c015dd317e68f10e190e4c)  
**Subject:** MCP `sku_id` field is always null — requesting seller SKU exposure

Hi Team,

We are building an internal operations system on top of the ShopDeck MCP Data API. We have noticed that the `sku_id` field in the `order_line_items` MCP table is consistently `null` across all our orders, despite us having seller-defined SKU codes configured in our ShopDeck catalog panel (e.g., `BLUSHBLOOM-FRLK-KDB-5PC`, `PASTEL-GARDEN-FRLK-5PC`, etc.).

**What we need:**

1. **Immediate:** Can the `sku_id` field in `order_line_items` be populated with the seller's own SKU code (the one the seller enters in the ShopDeck catalog)?

2. **Or alternatively:** Can a mapping table (e.g., `catalog` or `products` or `sku_variants`) be exposed through the MCP that maps `customer_sku_short_id` → seller SKU code → product name? Currently, the MCP has no such table.

**What we currently get in the MCP:**

| Field | Value |
|---|---|
| `sku_id` | `null` |
| `customer_sku_short_id` | `XUoDpuUg` (opaque ShopDeck hash) |
| `product_name` | `Blush Bloom Floral King size Bedsheet Set` |

The `customer_sku_short_id` is not resolvable to a seller SKU code through any exposed MCP endpoint.

**Why this matters:** We use the seller SKU code as the primary key to link ShopDeck order data to our internal Inventory, NDR automation, and warehouse systems. Without this bridge, we are forced to rely on fuzzy `product_name` matching which is brittle.

We would greatly appreciate either a fix to populate `sku_id` or an MCP catalog table addition in a future release.

Thank you.
