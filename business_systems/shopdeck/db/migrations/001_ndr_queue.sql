-- ================================================================
-- ShopDeck BS: NDR Queue Migration 001
-- Transactional, idempotent, safe to re-run.
-- Does NOT modify shipment_ndr_reports.
-- Does NOT create unique index on shipment_ndr_reports.
-- ================================================================

BEGIN;

-- ================================================================
-- TABLE: ndr_queue
-- ShopDeck BS owns the NDR work queue entirely.
-- Natural key: (awb_no, ndr_attempt_seq) where ndr_attempt_seq = ndr_count at enrollment.
-- ================================================================
CREATE TABLE IF NOT EXISTS ndr_queue (
    queue_item_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    awb_no                  TEXT NOT NULL,
    ndr_attempt_seq         INTEGER NOT NULL,
    queue_status            TEXT NOT NULL DEFAULT 'eligible',
    enrolled_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ndr_time_at_enroll      TIMESTAMPTZ NOT NULL,
    ndr_reason_at_enroll    TEXT,
    ndr_count_at_enroll     INTEGER NOT NULL,
    payment_mode            TEXT NOT NULL,
    claimed_by              TEXT,
    claimed_at              TIMESTAMPTZ,
    lease_expires_at        TIMESTAMPTZ,
    claim_attempt_count     INTEGER NOT NULL DEFAULT 0,
    max_claim_attempts      INTEGER NOT NULL DEFAULT 5,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    max_retries             INTEGER NOT NULL DEFAULT 2,
    last_failure_reason     TEXT,
    last_failure_class      TEXT,
    action_ready_at         TIMESTAMPTZ,
    terminal_at             TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ndr_queue_awb_attempt UNIQUE (awb_no, ndr_attempt_seq)
);

CREATE INDEX IF NOT EXISTS idx_ndr_queue_eligible
    ON ndr_queue (ndr_attempt_seq ASC, ndr_time_at_enroll ASC)
    WHERE queue_status = 'eligible';

CREATE INDEX IF NOT EXISTS idx_ndr_queue_claimable
    ON ndr_queue (lease_expires_at)
    WHERE queue_status = 'claimed';

CREATE INDEX IF NOT EXISTS idx_ndr_queue_awb
    ON ndr_queue (awb_no);

CREATE INDEX IF NOT EXISTS idx_ndr_queue_status
    ON ndr_queue (queue_status);

-- ================================================================
-- TABLE: ndr_engagements
-- Pre-registered BEFORE physical call dispatch.
-- One queue item may have multiple historical engagements.
-- ================================================================
CREATE TABLE IF NOT EXISTS ndr_engagements (
    engagement_id           TEXT PRIMARY KEY,
    queue_item_id           UUID NOT NULL REFERENCES ndr_queue(queue_item_id),
    awb_no                  TEXT NOT NULL,
    idempotency_key         TEXT NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    call_sid                TEXT,
    call_outcome            TEXT,
    transcript_id           TEXT,
    transcript_summary      TEXT,
    dispatched_at           TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ndr_engagements_idempotency UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_ndr_engagements_queue_item
    ON ndr_engagements (queue_item_id);

CREATE INDEX IF NOT EXISTS idx_ndr_engagements_active
    ON ndr_engagements (queue_item_id)
    WHERE is_active = TRUE;

-- ================================================================
-- TABLE: ndr_intelligence_results
-- Durable intelligence from NDR-ID. result_id is Brain idempotency key.
-- ================================================================
CREATE TABLE IF NOT EXISTS ndr_intelligence_results (
    result_id               TEXT PRIMARY KEY,
    queue_item_id           UUID NOT NULL REFERENCES ndr_queue(queue_item_id),
    engagement_id           TEXT NOT NULL REFERENCES ndr_engagements(engagement_id),
    awb_no                  TEXT NOT NULL,
    recommended_action      TEXT NOT NULL,
    diagnosis               TEXT,
    customer_intent         TEXT,
    confidence_level        TEXT,
    provenance              TEXT,
    action_parameters       JSONB NOT NULL DEFAULT '{}',
    reasoning               TEXT,
    risk_score              TEXT,
    source_evidence         JSONB NOT NULL DEFAULT '[]',
    submitted_by            TEXT,
    persisted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ndr_intelligence_engagement UNIQUE (engagement_id)
);

CREATE INDEX IF NOT EXISTS idx_ndr_intelligence_queue
    ON ndr_intelligence_results (queue_item_id);

COMMIT;
