-- =============================================================================
-- SOVEREIGN CATALOG BUSINESS SYSTEM (CATALOG BS) - POSTGRESQL SCHEMA DDL
-- Authoritative Specification Version: 1.3
-- Bounded Context: Box 4 (Catalog Business System)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. TABLE: catalog_products
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_products (
    internal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code VARCHAR(24) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    product_type VARCHAR(128),
    brand VARCHAR(64) NOT NULL DEFAULT 'Aaram Homes',
    hsn_code VARCHAR(10),
    gst_percentage NUMERIC(4, 2) NOT NULL DEFAULT 5.00,
    fabric_type TEXT,
    care_instructions TEXT,
    set_composition TEXT,
    product_media_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    size_chart_url TEXT,
    video_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    collection_tags TEXT[] NOT NULL DEFAULT '{}'::text[],
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_catalog_products_code UNIQUE (product_code),
    CONSTRAINT chk_product_code_format CHECK (
        product_code ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$' AND
        char_length(product_code) >= 5 AND
        char_length(product_code) < 25
    ),
    CONSTRAINT chk_product_name_minlen CHECK (char_length(name) >= 5),
    CONSTRAINT chk_product_hsn_len CHECK (hsn_code IS NULL OR char_length(hsn_code) >= 4),
    CONSTRAINT chk_product_gst_range CHECK (gst_percentage >= 0.0 AND gst_percentage <= 100.0),
    CONSTRAINT chk_product_lifecycle CHECK (
        lifecycle_state IN ('DRAFT', 'READY', 'PUBLISHED')
    )
);

-- Ensure created_at and updated_at exist if table was created in an older migration
ALTER TABLE catalog_products ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE catalog_products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- -----------------------------------------------------------------------------
-- 2. TABLE: catalog_skus
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_skus (
    internal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_internal_id UUID NOT NULL,
    sku_id VARCHAR(10) NOT NULL,
    colour VARCHAR(64),
    size VARCHAR(64),
    size_type VARCHAR(32),
    pack_configuration VARCHAR(64),
    mrp NUMERIC(10, 2) NOT NULL,
    selling_price NUMERIC(10, 2) NOT NULL,
    cost_price NUMERIC(10, 2) NOT NULL,
    packaging_length_cm NUMERIC(6, 2) NOT NULL,
    packaging_breadth_cm NUMERIC(6, 2) NOT NULL,
    packaging_height_cm NUMERIC(6, 2) NOT NULL,
    packaging_weight_kg NUMERIC(6, 3) NOT NULL,
    sku_media_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_catalog_skus_product FOREIGN KEY (product_internal_id)
        REFERENCES catalog_products(internal_id) ON DELETE RESTRICT,
    CONSTRAINT uq_catalog_skus_sku_id UNIQUE (sku_id),
    CONSTRAINT chk_sku_id_format CHECK (
        sku_id ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$' AND
        char_length(sku_id) >= 5 AND
        char_length(sku_id) <= 10
    ),
    CONSTRAINT chk_sku_mrp_pos CHECK (mrp > 0),
    CONSTRAINT chk_sku_selling_price_pos CHECK (selling_price > 0),
    CONSTRAINT chk_sku_cost_price_pos CHECK (cost_price > 0),
    CONSTRAINT chk_sku_price_ceiling CHECK (selling_price <= mrp),
    CONSTRAINT chk_sku_dim_length CHECK (packaging_length_cm >= 1.0 AND packaging_length_cm <= 50.0),
    CONSTRAINT chk_sku_dim_breadth CHECK (packaging_breadth_cm >= 1.0 AND packaging_breadth_cm <= 50.0),
    CONSTRAINT chk_sku_dim_height CHECK (packaging_height_cm >= 1.0 AND packaging_height_cm <= 50.0),
    CONSTRAINT chk_sku_dim_weight CHECK (packaging_weight_kg >= 0.050 AND packaging_weight_kg <= 10.000),
    CONSTRAINT chk_sku_size_type CHECK (size_type IS NULL OR size_type IN ('size', 'variant'))
);

-- Index for FK lookups and sibling assembly
CREATE INDEX IF NOT EXISTS idx_catalog_skus_product_id ON catalog_skus(product_internal_id);

-- Ensure created_at and updated_at exist if table was created in an older migration
ALTER TABLE catalog_skus ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE catalog_skus ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- -----------------------------------------------------------------------------
-- 3. TABLE: catalog_sku_id_reservations (Permanent Business Key Registry)
-- Enforces Rule RET-02 / ADR-RUL-002: Permanent SKU-ID historical non-reuse.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_sku_id_reservations (
    sku_id VARCHAR(10) PRIMARY KEY,
    sku_internal_id UUID NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sku_id_res_sku FOREIGN KEY (sku_internal_id)
        REFERENCES catalog_skus(internal_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_sku_res_internal ON catalog_sku_id_reservations(sku_internal_id);

-- Enforce Rule RET-02: Concurrency-safe permanent SKU-ID reservation trigger
CREATE OR REPLACE FUNCTION fn_catalog_reserve_sku_id()
RETURNS TRIGGER AS $$
DECLARE
    v_existing_owner UUID;
BEGIN
    -- 1. Atomically insert reservation. If sku_id exists, row lock is acquired on conflict.
    INSERT INTO catalog_sku_id_reservations (sku_id, sku_internal_id)
    VALUES (NEW.sku_id, NEW.internal_id)
    ON CONFLICT (sku_id) DO NOTHING;

    -- 2. Inspect authoritative owner under row-level lock (FOR SHARE)
    SELECT sku_internal_id INTO v_existing_owner
    FROM catalog_sku_id_reservations
    WHERE sku_id = NEW.sku_id
    FOR SHARE;

    IF v_existing_owner IS NULL OR v_existing_owner <> NEW.internal_id THEN
        RAISE EXCEPTION 'SKU ID % is permanently reserved for SKU entity % and cannot be assigned to % (Rule RET-02).',
            NEW.sku_id, v_existing_owner, NEW.internal_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_catalog_skus_reserve_sku_id
AFTER INSERT OR UPDATE OF sku_id ON catalog_skus
FOR EACH ROW EXECUTE FUNCTION fn_catalog_reserve_sku_id();

-- -----------------------------------------------------------------------------
-- 4. TABLE: catalog_product_code_reservations (Permanent Product Key Registry)
-- Enforces Rule PRD-05 / ADR-RUL-008: Permanent Product Code historical non-reuse.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_product_code_reservations (
    product_code VARCHAR(24) PRIMARY KEY,
    product_internal_id UUID NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_product_code_res_product FOREIGN KEY (product_internal_id)
        REFERENCES catalog_products(internal_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_prod_code_res_internal ON catalog_product_code_reservations(product_internal_id);

-- Enforce Rule PRD-05: Concurrency-safe permanent Product Code reservation trigger
CREATE OR REPLACE FUNCTION fn_catalog_reserve_product_code()
RETURNS TRIGGER AS $$
DECLARE
    v_existing_owner UUID;
BEGIN
    -- 1. Atomically insert reservation. If product_code exists, row lock is acquired on conflict.
    INSERT INTO catalog_product_code_reservations (product_code, product_internal_id)
    VALUES (NEW.product_code, NEW.internal_id)
    ON CONFLICT (product_code) DO NOTHING;

    -- 2. Inspect authoritative owner under row-level lock (FOR SHARE)
    SELECT product_internal_id INTO v_existing_owner
    FROM catalog_product_code_reservations
    WHERE product_code = NEW.product_code
    FOR SHARE;

    IF v_existing_owner IS NULL OR v_existing_owner <> NEW.internal_id THEN
        RAISE EXCEPTION 'Product Code % is permanently reserved for Product entity % and cannot be assigned to % (Rule PRD-05 / ADR-RUL-008).',
            NEW.product_code, v_existing_owner, NEW.internal_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_catalog_products_reserve_product_code
AFTER INSERT OR UPDATE OF product_code ON catalog_products
FOR EACH ROW EXECUTE FUNCTION fn_catalog_reserve_product_code();

-- Prevent direct mutations or deletions of reservation ledgers
CREATE OR REPLACE FUNCTION fn_catalog_prevent_reservation_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Permanent key reservations cannot be updated or deleted.';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_sku_id_res_immutable
BEFORE UPDATE OR DELETE ON catalog_sku_id_reservations
FOR EACH ROW EXECUTE FUNCTION fn_catalog_prevent_reservation_mutation();

CREATE OR REPLACE TRIGGER trg_prod_code_res_immutable
BEFORE UPDATE OR DELETE ON catalog_product_code_reservations
FOR EACH ROW EXECUTE FUNCTION fn_catalog_prevent_reservation_mutation();

-- -----------------------------------------------------------------------------
-- 5. TABLE: catalog_price_history (Immutable Ledger)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_price_history (
    id BIGSERIAL PRIMARY KEY,
    sku_internal_id UUID NOT NULL,
    previous_selling_price NUMERIC(10, 2),
    new_selling_price NUMERIC(10, 2) NOT NULL,
    previous_mrp NUMERIC(10, 2),
    new_mrp NUMERIC(10, 2) NOT NULL,
    previous_cost_price NUMERIC(10, 2),
    new_cost_price NUMERIC(10, 2) NOT NULL,
    changed_by TEXT NOT NULL DEFAULT 'SYSTEM',
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_price_history_sku FOREIGN KEY (sku_internal_id)
        REFERENCES catalog_skus(internal_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_price_history_sku ON catalog_price_history(sku_internal_id);

-- Enforce physical immutability at database boundary (No UPDATE or DELETE allowed on price history)
CREATE OR REPLACE FUNCTION fn_catalog_prevent_price_history_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'catalog_price_history is an immutable ledger: UPDATE and DELETE operations are strictly prohibited.';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_catalog_price_history_immutable
BEFORE UPDATE OR DELETE ON catalog_price_history
FOR EACH ROW EXECUTE FUNCTION fn_catalog_prevent_price_history_mutation();

-- -----------------------------------------------------------------------------
-- 6. TABLE: catalog_channel_mappings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_channel_mappings (
    id BIGSERIAL PRIMARY KEY,
    channel VARCHAR(32) NOT NULL DEFAULT 'SHOPDECK',
    sku_internal_id UUID NOT NULL,
    external_sku_token VARCHAR(64) NOT NULL,
    external_product_token VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_channel_map_sku FOREIGN KEY (sku_internal_id)
        REFERENCES catalog_skus(internal_id) ON DELETE RESTRICT,
    CONSTRAINT uq_channel_sku_token UNIQUE (channel, external_sku_token),
    CONSTRAINT uq_channel_sku_internal UNIQUE (channel, sku_internal_id)
);

CREATE INDEX IF NOT EXISTS idx_channel_map_lookup ON catalog_channel_mappings(sku_internal_id);

-- -----------------------------------------------------------------------------
-- 7. TABLE: catalog_publication_artifacts (Dual-Resource Safe Pipeline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_publication_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(32) NOT NULL DEFAULT 'SHOPDECK',
    artifact_type VARCHAR(32) NOT NULL DEFAULT 'CSV_46_COLUMN',
    file_path TEXT NOT NULL,
    content_hash VARCHAR(64),
    exported_sku_count INTEGER NOT NULL CHECK (exported_sku_count >= 0),
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS',
    generated_by TEXT NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '10 minutes'),
    finalized_at TIMESTAMPTZ,
    error_message TEXT,

    CONSTRAINT chk_pub_artifact_status CHECK (
        status IN ('IN_PROGRESS', 'COMMITTED', 'FAILED')
    )
);

CREATE INDEX IF NOT EXISTS idx_pub_artifacts_status_expiry ON catalog_publication_artifacts(status, expires_at);

-- -----------------------------------------------------------------------------
-- 8. TABLE: catalog_idempotency_records
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_idempotency_records (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    operation VARCHAR(64) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempotency_expiry ON catalog_idempotency_records(expires_at);

-- -----------------------------------------------------------------------------
-- 9. AUTOMATED TIMESTAMP UPDATE TRIGGERS
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_catalog_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_catalog_products_updated_at
BEFORE UPDATE ON catalog_products
FOR EACH ROW EXECUTE FUNCTION fn_catalog_set_updated_at();

CREATE OR REPLACE TRIGGER trg_catalog_skus_updated_at
BEFORE UPDATE ON catalog_skus
FOR EACH ROW EXECUTE FUNCTION fn_catalog_set_updated_at();

CREATE OR REPLACE TRIGGER trg_catalog_channel_mappings_updated_at
BEFORE UPDATE ON catalog_channel_mappings
FOR EACH ROW EXECUTE FUNCTION fn_catalog_set_updated_at();

-- -----------------------------------------------------------------------------
-- 10. PUBLIC READ PROJECTIONS (STABLE CONTRACT VIEWS)
-- -----------------------------------------------------------------------------

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
