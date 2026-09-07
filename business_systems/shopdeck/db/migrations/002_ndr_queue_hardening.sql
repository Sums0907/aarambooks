-- ================================================================
-- ShopDeck BS: NDR Queue Hardening Migration 002
-- Replaces standard index with unique index for active engagements
-- ================================================================

BEGIN;

-- Drop the non-unique index from 001
DROP INDEX IF EXISTS idx_ndr_engagements_active;

-- Create the required UNIQUE index to enforce exactly one active engagement per queue item
CREATE UNIQUE INDEX IF NOT EXISTS uq_ndr_engagements_active
    ON ndr_engagements (queue_item_id)
    WHERE is_active = TRUE;

COMMIT;
