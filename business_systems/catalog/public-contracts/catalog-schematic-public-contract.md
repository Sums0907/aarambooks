---
source_bs: "catalog"
namespace_name: "catalog"
namespace_classification: "AARAM_NATIVE"
namespace_description: "Aaram Catalog Business System — commercial product and SKU knowledge"
contract_version: "1.0"
---

# Aaram Catalog Schematic Public Contract

### View: vw_catalog_products
- **Description:** Product-level commercial data. One row per Product (commercial family).

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| product_internal_id | TEXT | false | false | None | Technical primary key (AZM does NOT use this as its UUID) |
| product_code | TEXT | false | false | None | Commercial grouping code for sibling SKUs |
| product_name | TEXT | false | false | catalog.entity.product | Commercial title of the product |
| description | TEXT | false | false | catalog.entity.product | Storytelling narrative description |
| product_type | TEXT | false | false | None | Type classification of the product |
| brand | TEXT | false | false | None | Brand name |
| hsn_code | TEXT | false | false | None | Harmonised System Nomenclature code for GST |
| gst_percentage | NUMERIC | false | false | None | GST rate applicable to this product |
| fabric_type | TEXT | false | false | None | Material / fabric composition |
| care_instructions | TEXT | false | false | None | Washing and care guidelines |
| set_composition | TEXT | false | false | None | Set/bundle composition description |
| product_media_urls | TEXT | false | false | None | Lifestyle media URLs (JSON array) |
| size_chart_url | TEXT | false | false | None | Size chart image URL |
| video_urls | TEXT | false | false | None | Product video URLs (JSON array) |
| collection_tags | TEXT | false | false | None | Collection/category tags (JSON array) |
| lifecycle_state | TEXT | false | false | None | Catalog BS lifecycle status (DRAFT/ACTIVE/ARCHIVED) |
| created_at | TIMESTAMP | false | false | None | Record creation timestamp |
| updated_at | TIMESTAMP | false | false | None | Record last-updated timestamp |

### View: vw_catalog_skus
- **Description:** SKU-level sellable unit data. One row per physical sellable variant.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| sku_internal_id | TEXT | false | false | None | Technical SKU primary key |
| product_internal_id | TEXT | false | false | None | Technical product primary key (FK) |
| product_code | TEXT | false | false | None | Parent product code |
| product_name | TEXT | false | false | catalog.entity.product | Parent product commercial title |
| sku_id | TEXT | false | false | None | Sovereign operational key (e.g. 126BS-RED) |
| colour | TEXT | false | false | catalog.entity.sku | Physical colour variation |
| size | TEXT | false | false | catalog.entity.sku | Physical size variation |
| size_type | TEXT | false | false | None | Size type classification (e.g. numeric, alpha) |
| pack_configuration | TEXT | false | false | None | Packing configuration (e.g. single, set) |
| mrp | NUMERIC | false | false | catalog.entity.sku | Maximum Retail Price |
| selling_price | NUMERIC | false | false | catalog.entity.sku | Storefront base selling price |
| cost_price | NUMERIC | false | false | catalog.entity.sku | Manufactured cost price |
| gross_margin | NUMERIC | true | false | catalog.entity.sku | Derived: selling_price - cost_price |
| packaging_length_cm | NUMERIC | false | false | catalog.entity.sku | Packaging length in centimetres |
| packaging_breadth_cm | NUMERIC | false | false | catalog.entity.sku | Packaging breadth in centimetres |
| packaging_height_cm | NUMERIC | false | false | catalog.entity.sku | Packaging height in centimetres |
| packaging_weight_kg | NUMERIC | false | false | catalog.entity.sku | Packaging weight in kilograms |
| sku_media_urls | TEXT | false | false | None | SKU physical swatch media URLs (JSON array) |
| created_at | TIMESTAMP | false | false | None | Record creation timestamp |
| updated_at | TIMESTAMP | false | false | None | Record last-updated timestamp |

### View: vw_catalog_master
- **Description:** Unified read projection combining Product + SKU + channel mapping tokens.

| Column | Type | Is Derived | Is Channel Field | Semantic Key | Description |
|---|---|---|---|---|---|
| sku_internal_id | TEXT | false | false | None | Technical SKU primary key |
| product_internal_id | TEXT | false | false | None | Technical product primary key |
| sku_id | TEXT | false | false | None | Sovereign operational SKU key |
| product_code | TEXT | false | false | None | Parent product code |
| product_name | TEXT | false | false | catalog.entity.product | Parent product name |
| description | TEXT | false | false | None | Product description |
| product_type | TEXT | false | false | None | Product type classification |
| brand | TEXT | false | false | None | Brand name |
| hsn_code | TEXT | false | false | None | HSN code |
| gst_percentage | NUMERIC | false | false | None | GST rate |
| fabric_type | TEXT | false | false | None | Fabric composition |
| care_instructions | TEXT | false | false | None | Care guidelines |
| set_composition | TEXT | false | false | None | Set composition |
| colour | TEXT | false | false | catalog.entity.sku | Colour variation |
| size | TEXT | false | false | catalog.entity.sku | Size variation |
| size_type | TEXT | false | false | None | Size type |
| pack_configuration | TEXT | false | false | None | Pack configuration |
| mrp | NUMERIC | false | false | catalog.entity.sku | Maximum Retail Price |
| selling_price | NUMERIC | false | false | catalog.entity.sku | Storefront base selling price |
| cost_price | NUMERIC | false | false | catalog.entity.sku | Manufactured cost price |
| gross_margin | NUMERIC | true | false | catalog.entity.sku | Derived: selling_price - cost_price |
| packaging_length_cm | NUMERIC | false | false | catalog.entity.sku | Packaging length cm |
| packaging_breadth_cm | NUMERIC | false | false | catalog.entity.sku | Packaging breadth cm |
| packaging_height_cm | NUMERIC | false | false | catalog.entity.sku | Packaging height cm |
| packaging_weight_kg | NUMERIC | false | false | catalog.entity.sku | Packaging weight kg |
| sku_media_urls | TEXT | false | false | None | SKU media URLs |
| product_media_urls | TEXT | false | false | None | Product media URLs |
| size_chart_url | TEXT | false | false | None | Size chart URL |
| video_urls | TEXT | false | false | None | Video URLs |
| collection_tags | TEXT | false | false | None | Collection tags |
| lifecycle_state | TEXT | false | false | None | Product lifecycle state |
| shopdeck_sku_id | TEXT | false | true | None | ShopDeck channel SKU token (EXTERNAL_CHANNEL) |
| shopdeck_product_id | TEXT | false | true | None | ShopDeck channel product token (EXTERNAL_CHANNEL) |
| created_at | TIMESTAMP | false | false | None | Creation timestamp |
| updated_at | TIMESTAMP | false | false | None | Last-updated timestamp |
