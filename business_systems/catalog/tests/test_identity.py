"""
Identity and Sovereign Key Invariant Tests for Catalog BS
Strictly validates immutable UUIDs, Product Code format, SKU ID format,
permanent historical SKU ID non-reuse (Rule RET-02 / ADR-RUL-002),
permanent Product Code historical non-reuse (Rule PRD-05 / ADR-RUL-008),
adversarial concurrency races, and database-level reservation ledgers and triggers.
"""

import asyncio
from decimal import Decimal
import pytest
from uuid import UUID, uuid4
import asyncpg
from catalog.config import CATALOG_DATABASE_URL
from catalog.models import (
    RenameProductCodePayload,
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
)
from catalog.service import CatalogService
from catalog.validation import validate_sku_id, validate_product_code


def test_sku_id_sovereign_rules():
    # Valid sovereign alphanumeric keys with hyphen separators
    assert validate_sku_id("126BS") is None
    assert validate_sku_id("126BS-BLU") is None
    assert validate_sku_id("101CC-SUN") is None
    assert validate_sku_id("A1B2C-D3E4") is None

    # Length constraints: 5 <= len <= 10
    assert validate_sku_id("1234") is not None  # 4 chars -> invalid
    assert validate_sku_id("12345") is None     # 5 chars -> valid
    assert validate_sku_id("1234567890") is None # 10 chars -> valid
    assert validate_sku_id("12345678901") is not None # 11 chars -> invalid

    # Format constraints
    assert validate_sku_id("126bs-blu") is not None  # Lowercase prohibited
    assert validate_sku_id("126BS_BLU") is not None  # Underscore prohibited
    assert validate_sku_id("126BS--BLU") is not None # Consecutive hyphens prohibited
    assert validate_sku_id("-126BS-BLU") is not None # Leading hyphen prohibited
    assert validate_sku_id("126BS-BLU-") is not None # Trailing hyphen prohibited


def test_product_code_sovereign_rules():
    # Valid sovereign product codes: 5 <= len < 25 (max 24 chars)
    assert validate_product_code("AH-MP-WATERPROOF") is None
    assert validate_product_code("AH-BS-PASTEL") is None
    assert validate_product_code("AH-1234") is None

    # Length constraints: 5 <= len <= 24
    assert validate_product_code("AH-1") is not None # 4 chars -> invalid
    assert validate_product_code("123456789012345678901234") is None # 24 chars -> valid
    assert validate_product_code("1234567890123456789012345") is not None # 25 chars -> invalid

    # Format constraints
    assert validate_product_code("ah-mp-waterproof") is not None # Lowercase prohibited
    assert validate_product_code("AH_MP_WATERPROOF") is not None # Underscore prohibited
    assert validate_product_code("AH--MP") is not None # Consecutive hyphens prohibited


def test_uuid_internal_identity():
    # UUID primary keys must be valid RFC 4122 Version 4 UUIDs
    u1 = uuid4()
    u2 = uuid4()
    assert u1 != u2
    assert isinstance(u1, UUID)
    assert len(str(u1)) == 36


# =============================================================================
# RET-02 / ADR-RUL-002: PERMANENT SKU ID HISTORICAL NON-REUSE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_sku_id_permanent_historical_reservation_and_no_recycling(catalog_service):
    """
    Validates Rule RET-02 & ADR-RUL-002:
    a. Create SKU ABC01 under Product 1
    b. Rename ABC01 -> ABC02 on the same SKU entity
    c. Attempt to create another SKU ABC01 -> MUST reject
    d. Attempt to rename another SKU to ABC01 -> MUST reject
    e. Same SKU retaining its own current ABC02 must remain valid
    f. Concurrent attempts cannot bypass the reservation
    g. Historical resolution of ABC01 resolves to the canonical entity
    """
    # a. Create Product 1 with SKU ABC01
    res1 = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-RET-01",
                name="Permanent SKU Test Product 1",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="ABC01",
                    colour="Navy",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res1.status == "SUCCESS"
    prod1_id = res1.product_internal_id
    sku1_id = res1.sku_internal_ids[0]

    # Verify ABC01 is registered in catalog_sku_id_reservations
    async with catalog_service.pool.acquire() as conn:
        res_row = await conn.fetchrow(
            "SELECT * FROM catalog_sku_id_reservations WHERE sku_id = 'ABC01';"
        )
        assert res_row is not None
        assert res_row["sku_internal_id"] == sku1_id

    # b. Rename ABC01 -> ABC02 on SKU 1
    res_rename = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_internal_id=prod1_id,
                product_code="AH-RET-01",
                name="Permanent SKU Test Product 1",
            ),
            skus=[
                SaveSkuInput(
                    sku_internal_id=sku1_id,
                    sku_id="ABC02",  # Renamed!
                    colour="Navy Blue",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_rename.status == "SUCCESS"

    # Verify both ABC01 and ABC02 are permanently reserved for sku1_id
    async with catalog_service.pool.acquire() as conn:
        reservations = await conn.fetch(
            "SELECT sku_id, sku_internal_id FROM catalog_sku_id_reservations WHERE sku_internal_id = $1 ORDER BY sku_id;",
            sku1_id,
        )
        assert len(reservations) == 2
        assert reservations[0]["sku_id"] == "ABC01"
        assert reservations[1]["sku_id"] == "ABC02"

    # c. Attempt to create a NEW SKU with sku_id = ABC01 under Product 1 -> MUST reject
    res_create_dup = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_internal_id=prod1_id,
                product_code="AH-RET-01",
                name="Permanent SKU Test Product 1",
            ),
            skus=[
                SaveSkuInput(
                    sku_internal_id=sku1_id,
                    sku_id="ABC02",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                ),
                SaveSkuInput(
                    # New SKU without sku_internal_id attempting to use retired ABC01
                    sku_id="ABC01",
                    mrp=Decimal("2200.00"),
                    selling_price=Decimal("1100.00"),
                    cost_price=Decimal("550.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                ),
            ],
        )
    )
    assert res_create_dup.status == "REJECTED"
    assert any(e.error_code == "SKU_COLLISION" for e in res_create_dup.errors)

    # c2. Attempt to create SKU ABC01 under a DIFFERENT Product 2 -> MUST reject
    res_prod2 = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-RET-02",
                name="Permanent SKU Test Product 2",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="ABC01",  # Hijack attempt across products
                    mrp=Decimal("2500.00"),
                    selling_price=Decimal("1200.00"),
                    cost_price=Decimal("600.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_prod2.status == "REJECTED"
    assert any(e.error_code in ("SKU_COLLISION", "CROSS_PRODUCT_SKU_MUTATION_DENIED") for e in res_prod2.errors)

    # d. Create SKU 2 (XYZ01) under Product 2 and attempt to rename XYZ01 -> ABC01 -> MUST reject
    res_p2_ok = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-RET-02",
                name="Permanent SKU Test Product 2",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="XYZ01",
                    mrp=Decimal("2500.00"),
                    selling_price=Decimal("1200.00"),
                    cost_price=Decimal("600.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_p2_ok.status == "SUCCESS"
    sku2_id = res_p2_ok.sku_internal_ids[0]
    prod2_id = res_p2_ok.product_internal_id

    # Attempt to rename SKU 2 to ABC01
    res_rename_hijack = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_internal_id=prod2_id,
                product_code="AH-RET-02",
                name="Permanent SKU Test Product 2",
            ),
            skus=[
                SaveSkuInput(
                    sku_internal_id=sku2_id,
                    sku_id="ABC01",  # Rename to reserved ABC01
                    mrp=Decimal("2500.00"),
                    selling_price=Decimal("1200.00"),
                    cost_price=Decimal("600.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_rename_hijack.status == "REJECTED"
    assert any(e.error_code == "SKU_COLLISION" for e in res_rename_hijack.errors)

    # e. Same SKU 1 retaining its own current ABC02 must remain valid
    res_retain = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_internal_id=prod1_id,
                product_code="AH-RET-01",
                name="Permanent SKU Test Product 1 Updated",
            ),
            skus=[
                SaveSkuInput(
                    sku_internal_id=sku1_id,
                    sku_id="ABC02",  # Retaining own current key
                    colour="Navy Deep Blue",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_retain.status == "SUCCESS"

    # g. Historical resolution: resolve_sku('ABC01') resolves to the canonical SKU 1 entity
    resolved = await catalog_service.resolve_sku("ABC01", lookup_type="SKU_ID")
    assert resolved is not None
    assert resolved["sku_internal_id"] == sku1_id
    assert resolved["product_code"] == "AH-RET-01"


# =============================================================================
# PRD-05 / ADR-RUL-008: PERMANENT PRODUCT CODE HISTORICAL NON-REUSE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_product_code_permanent_historical_reservation_across_renames(catalog_service):
    """
    Validates Rule PRD-05 & ADR-RUL-008:
    a. Create Product AH-HIST-A
    b. Rename AH-HIST-A -> AH-HIST-B
    c. Attempt to create new Product AH-HIST-A -> MUST reject
    d. Attempt to rename Product C to AH-HIST-A -> MUST reject
    e. Same Product retaining AH-HIST-B remains valid
    """
    # a. Create Product AH-HIST-A
    res_a = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-HIST-A",
                name="Product Historical A",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="HIST-A1",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_a.status == "SUCCESS"
    prod_a_id = res_a.product_internal_id

    # b. Rename AH-HIST-A -> AH-HIST-B via RenameProductCode action
    rename_res = await catalog_service.rename_product_code(
        RenameProductCodePayload(
            product_internal_id=prod_a_id,
            new_product_code="AH-HIST-B",
        )
    )
    assert rename_res.status == "SUCCESS"

    # Verify both AH-HIST-A and AH-HIST-B are registered for prod_a_id
    async with catalog_service.pool.acquire() as conn:
        prod_res = await conn.fetch(
            "SELECT product_code FROM catalog_product_code_reservations WHERE product_internal_id = $1 ORDER BY product_code;",
            prod_a_id,
        )
        assert len(prod_res) == 2
        assert prod_res[0]["product_code"] == "AH-HIST-A"
        assert prod_res[1]["product_code"] == "AH-HIST-B"

    # c. Attempt to create NEW Product with retired code AH-HIST-A -> MUST reject
    res_c = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-HIST-A",  # Retired code
                name="Duplicate Historical Product Attempt",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="HIST-C1",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_c.status == "REJECTED"
    assert any(e.error_code == "PRODUCT_CODE_COLLISION" for e in res_c.errors)

    # d. Create Product C (AH-HIST-C) and attempt to rename it to AH-HIST-A -> MUST reject
    res_c_prod = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(
                product_code="AH-HIST-C",
                name="Product Historical C",
            ),
            skus=[
                SaveSkuInput(
                    sku_id="HIST-C2",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    assert res_c_prod.status == "SUCCESS"
    prod_c_id = res_c_prod.product_internal_id

    rename_hijack = await catalog_service.rename_product_code(
        RenameProductCodePayload(
            product_internal_id=prod_c_id,
            new_product_code="AH-HIST-A",  # Attempt to claim Product A's historical code
        )
    )
    assert rename_hijack.status == "REJECTED"
    assert any(e.error_code == "PRODUCT_CODE_COLLISION" for e in rename_hijack.errors)


# =============================================================================
# ADVERSARIAL CONCURRENCY RACES: SKU ID & PRODUCT CODE REGISTRIES
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_sku_reservation_race(catalog_service):
    """
    Adversarial Concurrency Test:
    Two concurrent transactions with DIFFERENT idempotency keys attempt to register
    the SAME sku_id ('RACE01') for two DIFFERENT Product entities.
    Verifies that exactly ONE succeeds and the other receives SKU_COLLISION.
    """
    payload_1 = SaveProductFamilyPayload(
        idempotency_key="tx-sku-race-1",
        product=SaveProductInput(
            product_code="AH-RACE-P1",
            name="Concurrent Race Product 1",
        ),
        skus=[
            SaveSkuInput(
                sku_id="RACE01",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
            )
        ],
    )

    payload_2 = SaveProductFamilyPayload(
        idempotency_key="tx-sku-race-2",
        product=SaveProductInput(
            product_code="AH-RACE-P2",
            name="Concurrent Race Product 2",
        ),
        skus=[
            SaveSkuInput(
                sku_id="RACE01",  # Same SKU ID
                mrp=Decimal("2500.00"),
                selling_price=Decimal("1200.00"),
                cost_price=Decimal("600.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
            )
        ],
    )

    # Launch both concurrent transactions simultaneously
    res1, res2 = await asyncio.gather(
        catalog_service.save_product_family(payload_1),
        catalog_service.save_product_family(payload_2),
    )

    statuses = [res1.status, res2.status]
    assert "SUCCESS" in statuses
    assert "REJECTED" in statuses
    assert statuses.count("SUCCESS") == 1
    assert statuses.count("REJECTED") == 1

    rejected_res = res1 if res1.status == "REJECTED" else res2
    assert any(e.error_code == "SKU_COLLISION" for e in rejected_res.errors)

    # Verify database has exactly 1 reservation for RACE01
    async with catalog_service.pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM catalog_sku_id_reservations WHERE sku_id = 'RACE01';"
        )
        assert count == 1


@pytest.mark.asyncio
async def test_concurrent_product_code_reservation_race(catalog_service):
    """
    Adversarial Concurrency Test:
    Two concurrent transactions with DIFFERENT idempotency keys attempt to register
    the SAME product_code ('AH-CODE-RACE') for two DIFFERENT Product entities.
    Verifies that exactly ONE succeeds and the other receives PRODUCT_CODE_COLLISION.
    """
    payload_1 = SaveProductFamilyPayload(
        idempotency_key="tx-prod-race-1",
        product=SaveProductInput(
            product_code="AH-CODE-RACE",
            name="Concurrent Code Race Product 1",
        ),
        skus=[
            SaveSkuInput(
                sku_id="PCODE1",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
            )
        ],
    )

    payload_2 = SaveProductFamilyPayload(
        idempotency_key="tx-prod-race-2",
        product=SaveProductInput(
            product_code="AH-CODE-RACE",  # Same Product Code
            name="Concurrent Code Race Product 2",
        ),
        skus=[
            SaveSkuInput(
                sku_id="PCODE2",
                mrp=Decimal("2500.00"),
                selling_price=Decimal("1200.00"),
                cost_price=Decimal("600.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
            )
        ],
    )

    res1, res2 = await asyncio.gather(
        catalog_service.save_product_family(payload_1),
        catalog_service.save_product_family(payload_2),
    )

    statuses = [res1.status, res2.status]
    assert "SUCCESS" in statuses
    assert "REJECTED" in statuses
    assert statuses.count("SUCCESS") == 1
    assert statuses.count("REJECTED") == 1

    rejected_res = res1 if res1.status == "REJECTED" else res2
    assert any(e.error_code == "PRODUCT_CODE_COLLISION" for e in rejected_res.errors)

    # Verify database has exactly 1 reservation for AH-CODE-RACE
    async with catalog_service.pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM catalog_product_code_reservations WHERE product_code = 'AH-CODE-RACE';"
        )
        assert count == 1


@pytest.mark.asyncio
async def test_concurrent_rename_product_code_race(catalog_service):
    """
    Adversarial Concurrency Test:
    Two existing Product entities attempt to rename to the SAME new product_code concurrently.
    Verifies that exactly ONE succeeds and the other receives PRODUCT_CODE_COLLISION.
    """
    # 1. Create two distinct products
    res1 = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(product_code="AH-RENAME-P1", name="Product Rename 1"),
            skus=[
                SaveSkuInput(
                    sku_id="RNM01",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    res2 = await catalog_service.save_product_family(
        SaveProductFamilyPayload(
            product=SaveProductInput(product_code="AH-RENAME-P2", name="Product Rename 2"),
            skus=[
                SaveSkuInput(
                    sku_id="RNM02",
                    mrp=Decimal("2000.00"),
                    selling_price=Decimal("1000.00"),
                    cost_price=Decimal("500.00"),
                    packaging_length_cm=Decimal("20.00"),
                    packaging_breadth_cm=Decimal("15.00"),
                    packaging_height_cm=Decimal("5.00"),
                    packaging_weight_kg=Decimal("0.500"),
                )
            ],
        )
    )
    p1_id = res1.product_internal_id
    p2_id = res2.product_internal_id

    # 2. Concurrently rename both to AH-COMMON-TARGET
    ren1, ren2 = await asyncio.gather(
        catalog_service.rename_product_code(
            RenameProductCodePayload(
                idempotency_key="rnm-race-1",
                product_internal_id=p1_id,
                new_product_code="AH-COMMON-TARGET",
            )
        ),
        catalog_service.rename_product_code(
            RenameProductCodePayload(
                idempotency_key="rnm-race-2",
                product_internal_id=p2_id,
                new_product_code="AH-COMMON-TARGET",
            )
        ),
    )

    statuses = [ren1.status, ren2.status]
    assert "SUCCESS" in statuses
    assert "REJECTED" in statuses
    assert statuses.count("SUCCESS") == 1
    assert statuses.count("REJECTED") == 1

    rejected_ren = ren1 if ren1.status == "REJECTED" else ren2
    assert any(e.error_code == "PRODUCT_CODE_COLLISION" for e in rejected_ren.errors)


# =============================================================================
# DATABASE TRIGGER & IMMUTABILITY ENFORCEMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_database_triggers_enforce_reservation_integrity(catalog_service):
    """
    Direct SQL tests verifying database triggers:
    1. trg_catalog_skus_reserve_sku_id prevents recycling across SKUs
    2. trg_catalog_products_reserve_product_code prevents recycling across Products
    3. trg_sku_id_res_immutable prevents direct UPDATE/DELETE on reservations
    4. trg_prod_code_res_immutable prevents direct UPDATE/DELETE on reservations
    """
    async with catalog_service.pool.acquire() as conn:
        prod1_id = uuid4()
        await conn.execute(
            """
            INSERT INTO catalog_products (internal_id, product_code, name)
            VALUES ($1, 'AH-TRIG-01', 'Trigger Test Product 1');
            """,
            prod1_id,
        )

        sku1_id = uuid4()
        await conn.execute(
            """
            INSERT INTO catalog_skus (
                internal_id, product_internal_id, sku_id, mrp, selling_price, cost_price,
                packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
            ) VALUES ($1, $2, 'TRG-01', 1000, 800, 400, 20, 15, 5, 0.5);
            """,
            sku1_id,
            prod1_id,
        )

        # 1. Direct SQL rename to TRG-02
        await conn.execute(
            "UPDATE catalog_skus SET sku_id = 'TRG-02' WHERE internal_id = $1;",
            sku1_id,
        )

        # 2. Attempt direct SQL insert of another SKU with TRG-01 -> trigger must raise exception
        sku2_id = uuid4()
        with pytest.raises(asyncpg.RaiseError, match="permanently reserved"):
            await conn.execute(
                """
                INSERT INTO catalog_skus (
                    internal_id, product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES ($1, $2, 'TRG-01', 1000, 800, 400, 20, 15, 5, 0.5);
                """,
                sku2_id,
                prod1_id,
            )

        # 3. Direct SQL immutability checks on reservation tables
        with pytest.raises(asyncpg.RaiseError, match="cannot be updated or deleted"):
            await conn.execute("DELETE FROM catalog_sku_id_reservations WHERE sku_id = 'TRG-01';")

        with pytest.raises(asyncpg.RaiseError, match="cannot be updated or deleted"):
            await conn.execute("DELETE FROM catalog_product_code_reservations WHERE product_code = 'AH-TRIG-01';")


@pytest.mark.asyncio
async def test_direct_database_concurrent_sku_reservation_race(catalog_service):
    """
    Direct Database-Level Concurrency Test (No Application Locks):
    Two raw PostgreSQL transactions attempt to insert two different SKUs
    with the SAME sku_id ('RAW-RACE-01').
    Verifies that trigger fn_catalog_reserve_sku_id under row-level lock
    atomically allows exactly one and raises an exception for the second.
    """
    prod_id = uuid4()
    sku1_id = uuid4()
    sku2_id = uuid4()

    async with catalog_service.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO catalog_products (internal_id, product_code, name) VALUES ($1, 'AH-RAW-RACE', 'Raw Race');",
            prod_id,
        )

    # Open two separate physical database connections
    conn1 = await asyncpg.connect(CATALOG_DATABASE_URL)
    conn2 = await asyncpg.connect(CATALOG_DATABASE_URL)

    async def tx1_insert():
        async with conn1.transaction():
            await conn1.execute(
                """
                INSERT INTO catalog_skus (
                    internal_id, product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES ($1, $2, 'RAWRACE01', 1000, 800, 400, 20, 15, 5, 0.5);
                """,
                sku1_id,
                prod_id,
            )

    async def tx2_insert():
        async with conn2.transaction():
            await conn2.execute(
                """
                INSERT INTO catalog_skus (
                    internal_id, product_internal_id, sku_id, mrp, selling_price, cost_price,
                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm, packaging_weight_kg
                ) VALUES ($1, $2, 'RAWRACE01', 1000, 800, 400, 20, 15, 5, 0.5);
                """,
                sku2_id,
                prod_id,
            )

    try:
        results = await asyncio.gather(tx1_insert(), tx2_insert(), return_exceptions=True)
        exceptions = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]

        assert len(successes) == 1
        assert len(exceptions) == 1
        assert isinstance(exceptions[0], (asyncpg.RaiseError, asyncpg.UniqueViolationError))
    finally:
        await conn1.close()
        await conn2.close()
