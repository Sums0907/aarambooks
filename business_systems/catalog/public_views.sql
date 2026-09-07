-- =============================================================================
-- SOVEREIGN CATALOG BUSINESS SYSTEM - PUBLIC READ PROJECTIONS
-- Authoritative Specification Version: 1.1
-- =============================================================================

-- VIEW: vw_catalog_products
CREATE OR REPLACE VIEW vw_catalog_products AS
SELECT
    p.internal_id AS product_internal_id,
    p.product_code,
    p.name AS product_name,
    p.description,
    p.product_type,
    p.brand,
    p.hsn_code,
    p.gst_percentage,
    p.fabric_type,
    p.care_instructions,
    p.set_composition,
    p.product_media_urls,
    p.size_chart_url,
    p.video_urls,
    p.collection_tags,
    p.lifecycle_state,
    p.created_at,
    p.updated_at
FROM catalog_products p;

-- VIEW: vw_catalog_skus
CREATE OR REPLACE VIEW vw_catalog_skus AS
SELECT
    s.internal_id AS sku_internal_id,
    s.product_internal_id,
    p.product_code,
    p.name AS product_name,
    s.sku_id,
    s.colour,
    s.size,
    s.size_type,
    s.pack_configuration,
    s.mrp,
    s.selling_price,
    s.cost_price,
    (s.selling_price - s.cost_price) AS gross_margin,
    s.packaging_length_cm,
    s.packaging_breadth_cm,
    s.packaging_height_cm,
    s.packaging_weight_kg,
    s.sku_media_urls,
    s.created_at,
    s.updated_at
FROM catalog_skus s
JOIN catalog_products p ON s.product_internal_id = p.internal_id;

-- VIEW: vw_catalog_master (Unified Read Contract for Ecosystem & ShopDeck Exporter)
CREATE OR REPLACE VIEW vw_catalog_master AS
SELECT
    s.internal_id AS sku_internal_id,
    p.internal_id AS product_internal_id,
    s.sku_id,
    p.product_code,
    p.name AS product_name,
    p.description,
    p.product_type,
    p.brand,
    p.hsn_code,
    p.gst_percentage,
    p.fabric_type,
    p.care_instructions,
    p.set_composition,
    s.colour,
    s.size,
    s.size_type,
    s.pack_configuration,
    s.mrp,
    s.selling_price,
    s.cost_price,
    (s.selling_price - s.cost_price) AS gross_margin,
    s.packaging_length_cm,
    s.packaging_breadth_cm,
    s.packaging_height_cm,
    s.packaging_weight_kg,
    s.sku_media_urls,
    p.product_media_urls,
    p.size_chart_url,
    p.video_urls,
    p.collection_tags,
    p.lifecycle_state,
    m.external_sku_token AS shopdeck_sku_id,
    m.external_product_token AS shopdeck_product_id,
    s.created_at,
    s.updated_at
FROM catalog_skus s
JOIN catalog_products p ON s.product_internal_id = p.internal_id
LEFT JOIN catalog_channel_mappings m ON s.internal_id = m.sku_internal_id AND m.channel = 'SHOPDECK';
