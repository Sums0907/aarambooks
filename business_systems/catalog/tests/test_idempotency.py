"""
Idempotency and Safe Mutation Tests for Catalog BS
Validates 24-hour persistent idempotency, conflict detection, concurrent execution safety, and TTL cleanup.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from catalog.config import CATALOG_DATABASE_URL
from catalog.models import (
    RenameProductCodePayload,
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
)
from catalog.service import CatalogService

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def catalog_service():
    service = await CatalogService.create(CATALOG_DATABASE_URL)
    yield service
    await service.close()

async def test_idempotent_mutation_flow(catalog_service):
    key = "idem-test-key-001"

    payload = SaveProductFamilyPayload(
        idempotency_key=key,
        product=SaveProductInput(
            product_code="AH-IDEM-01",
            name="Idempotency Test Product",
            brand="Aaram Homes",
        ),
        skus=[
            SaveSkuInput(
                sku_id="IDEM-SKU1",
                colour="Grey",
                size="Single",
                mrp=Decimal("1500.00"),
                selling_price=Decimal("799.00"),
                cost_price=Decimal("350.00"),
                packaging_length_cm=Decimal("25.00"),
                packaging_breadth_cm=Decimal("20.00"),
                packaging_height_cm=Decimal("4.00"),
                packaging_weight_kg=Decimal("0.600"),
            )
        ],
    )

    # 1. First execution -> SUCCESS
    res1 = await catalog_service.save_product_family(payload)
    assert res1.status == "SUCCESS"
    prod_id = res1.product_internal_id

    # 2. Repeated execution with identical payload & same key -> UNCHANGED_IDEMPOTENT
    res2 = await catalog_service.save_product_family(payload)
    assert res2.status == "UNCHANGED_IDEMPOTENT"
    assert res2.product_internal_id == prod_id
    assert res2.product_code == "AH-IDEM-01"

    # 3. Execution with same key but conflicting payload -> REJECTED (IDEMPOTENCY_CONFLICT)
    conflicting_payload = SaveProductFamilyPayload(
        idempotency_key=key,
        product=SaveProductInput(
            product_code="AH-IDEM-01-CONFLICT",
            name="Conflicting Product",
        ),
        skus=[],
    )
    res3 = await catalog_service.save_product_family(conflicting_payload)
    assert res3.status == "REJECTED"
    assert any(e.error_code == "IDEMPOTENCY_CONFLICT" for e in res3.errors)

    # 4. Persistence across service restarts: Create brand new service instance and test replay
    new_service = await CatalogService.create(CATALOG_DATABASE_URL)
    res4 = await new_service.save_product_family(payload)
    assert res4.status == "UNCHANGED_IDEMPOTENT"
    assert res4.product_internal_id == prod_id
    await new_service.close()

async def test_idempotent_operation_conflict(catalog_service):
    """Same key used across different operations must return IDEMPOTENCY_CONFLICT."""
    key = "idem-op-conflict-key"

    payload = SaveProductFamilyPayload(
        idempotency_key=key,
        product=SaveProductInput(
            product_code="AH-IDEM-OP",
            name="Idempotency Op Test",
        ),
        skus=[],
    )
    res1 = await catalog_service.save_product_family(payload)
    assert res1.status == "SUCCESS"
    prod_id = res1.product_internal_id

    # Attempt to use same idempotency key for RenameProductCode
    rename_payload = RenameProductCodePayload(
        idempotency_key=key,
        product_internal_id=prod_id,
        new_product_code="AH-IDEM-OP2",
    )
    res2 = await catalog_service.rename_product_code(rename_payload)
    assert res2.status == "REJECTED"
    assert any(e.error_code == "IDEMPOTENCY_CONFLICT" for e in res2.errors)

async def test_concurrent_idempotent_requests(catalog_service):
    """
    Validates concurrency safety (Part 6):
    Multiple simultaneous tasks using the same idempotency key must execute the mutation exactly once.
    """
    concurrent_key = "concurrent-key-999"

    payload = SaveProductFamilyPayload(
        idempotency_key=concurrent_key,
        product=SaveProductInput(
            product_code="AH-CONC-01",
            name="Concurrent Test Product",
            brand="Aaram Homes",
        ),
        skus=[
            SaveSkuInput(
                sku_id="CONC-SKU1",
                colour="Olive",
                size="Double",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1199.00"),
                cost_price=Decimal("450.00"),
                packaging_length_cm=Decimal("28.00"),
                packaging_breadth_cm=Decimal("22.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.900"),
            )
        ],
    )

    # Launch 5 parallel requests
    tasks = [catalog_service.save_product_family(payload) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # Exactly one request must return SUCCESS, the other 4 return UNCHANGED_IDEMPOTENT
    successes = [r for r in results if r.status == "SUCCESS"]
    idempotent_replays = [r for r in results if r.status == "UNCHANGED_IDEMPOTENT"]

    assert len(successes) == 1
    assert len(idempotent_replays) == 4

    # Verify exactly 1 product and 1 price history record exists in database
    async with catalog_service.pool.acquire() as conn:
        prod_count = await conn.fetchval(
            "SELECT count(*) FROM catalog_products WHERE product_code = 'AH-CONC-01';"
        )
        assert prod_count == 1

        ph_count = await conn.fetchval(
            "SELECT count(*) FROM catalog_price_history WHERE sku_internal_id IN (SELECT internal_id FROM catalog_skus WHERE sku_id = 'CONC-SKU1');"
        )
        assert ph_count == 1

async def test_idempotency_cleanup_and_expiry(catalog_service):
    """
    Validates idempotency TTL physical cleanup (Part 13).
    """
    expired_key = "expired-key-001"
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=2)

    async with catalog_service.pool.acquire() as conn:
        # Insert an expired record
        await conn.execute(
            """
            INSERT INTO catalog_idempotency_records (
                idempotency_key, operation, request_hash, response_payload, created_at, expires_at
            ) VALUES ($1, 'TestOp', 'hash123', '{"status": "SUCCESS"}'::jsonb, $2, $3);
            """,
            expired_key,
            now - timedelta(days=2),
            expired_time,
        )

    # Trigger cleanup
    deleted_count = await catalog_service.cleanup_expired_idempotency_records()
    assert deleted_count >= 1

    # Verify record no longer exists
    async with catalog_service.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM catalog_idempotency_records WHERE idempotency_key = $1;", expired_key
        )
        assert row is None
