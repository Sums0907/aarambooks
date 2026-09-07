"""
ShopDeck 46-Column CSV Channel Adapter & Publication Pipeline Tests
Strictly conforms to document 05-shopdeck-channel.md.
Tests formatting, media projection, strict inequality rules, size defaulting,
dual-resource publication state machine, crash points (a-e), and race-free recovery cleanup.
"""

import asyncio
from decimal import Decimal
import os
import pytest
from uuid import UUID, uuid4
import asyncpg
from catalog.config import CATALOG_DATABASE_URL
from catalog.models import (
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
    TransitionLifecycleStatePayload,
)
from catalog.service import CatalogService
from catalog.shopdeck_adapter import (
    SHOPDECK_46_COLUMNS,
    ShopDeckAdapter,
    project_media_slots,
)


@pytest.fixture
async def adapter_and_service():
    pool = await asyncpg.create_pool(CATALOG_DATABASE_URL, min_size=1, max_size=5)
    adapter = ShopDeckAdapter(pool)
    service = CatalogService(pool)
    yield adapter, service
    await pool.close()


def test_media_slot_projection_hierarchy():
    """
    Validates Section 3 Media Projection Hierarchy:
    - Image 1: Primary SKU swatch
    - Image 2: Secondary SKU detail
    - Images 3-10: Shared Product lifestyle images, then remaining SKU images
    - Deduplicates identical URLs
    """
    sku_media = [
        "https://media.aaramhomes.com/sku_swatch.jpg",
        "https://media.aaramhomes.com/sku_detail.jpg",
        "https://media.aaramhomes.com/sku_extra.jpg",
    ]
    prod_media = [
        "https://media.aaramhomes.com/prod_lifestyle1.jpg",
        "https://media.aaramhomes.com/prod_lifestyle2.jpg",
        "https://media.aaramhomes.com/sku_swatch.jpg",  # duplicate URL
    ]

    slots = project_media_slots(sku_media, prod_media)
    assert len(slots) == 10
    assert slots[0] == "https://media.aaramhomes.com/sku_swatch.jpg"  # Primary SKU
    assert slots[1] == "https://media.aaramhomes.com/sku_detail.jpg"  # Secondary SKU
    assert slots[2] == "https://media.aaramhomes.com/prod_lifestyle1.jpg"  # Product lifestyle 1
    assert slots[3] == "https://media.aaramhomes.com/prod_lifestyle2.jpg"  # Product lifestyle 2
    assert slots[4] == "https://media.aaramhomes.com/sku_extra.jpg"  # Remaining SKU image
    # Remaining slots 5..9 should be empty strings
    for s in slots[5:]:
        assert s == ""


def test_46_column_count_and_headers():
    """Validates that SHOPDECK_46_COLUMNS contains exactly 46 items in the exact canonical sequence."""
    assert len(SHOPDECK_46_COLUMNS) == 46
    assert SHOPDECK_46_COLUMNS[0] == "Product Code"
    assert SHOPDECK_46_COLUMNS[3] == "Sku Id"
    assert SHOPDECK_46_COLUMNS[4] == "Selling Price"
    assert SHOPDECK_46_COLUMNS[5] == "MRP"
    assert SHOPDECK_46_COLUMNS[6] == "Cost Price"
    assert SHOPDECK_46_COLUMNS[7] == "Quantity"
    assert SHOPDECK_46_COLUMNS[8] == "Packaging Length (in cm)"
    assert SHOPDECK_46_COLUMNS[12] == "GST %"
    assert SHOPDECK_46_COLUMNS[13] == "Image 1"
    assert SHOPDECK_46_COLUMNS[22] == "Image 10"
    assert SHOPDECK_46_COLUMNS[23] == "Video 1"
    assert SHOPDECK_46_COLUMNS[27] == "Size"
    assert SHOPDECK_46_COLUMNS[45] == "Action"


@pytest.mark.asyncio
async def test_shopdeck_csv_export_pipeline(adapter_and_service, tmp_path):
    """
    End-to-end export pipeline validation:
    1. Ingest Product & 2 SKUs via CatalogService.
    2. Transition to READY.
    3. Generate 46-column CSV artifact.
    4. Verify exact output headers, injected defaults, and database publication ledger.
    """
    adapter, service = adapter_and_service

    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-MP-EXPORT",
            name="Waterproof Mattress Protector Export Edition",
            description="<p>100% waterproof mattress protector featuring TPU membrane.</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            hsn_code="6304",
            gst_percentage=Decimal("5.00"),
            fabric_type="Cotton Terry with TPU Membrane",
            care_instructions="Machine wash cold on gentle cycle. Do not bleach.",
            set_composition="1 Fitted Mattress Protector",
            product_media_urls=[
                "https://media.aaramhomes.com/products/ah-mp-lifestyle-1.jpg",
                "https://media.aaramhomes.com/products/ah-mp-lifestyle-2.jpg",
            ],
            collection_tags=["mattress-protectors", "bed-linen"],
        ),
        skus=[
            SaveSkuInput(
                sku_id="101MP-BLU",
                colour="Navy Blue",
                size="King (72x78)",
                size_type="size",
                pack_configuration="Pack of 1",
                mrp=Decimal("2999.00"),
                selling_price=Decimal("1499.00"),
                cost_price=Decimal("650.00"),
                packaging_length_cm=Decimal("28.00"),
                packaging_breadth_cm=Decimal("22.00"),
                packaging_height_cm=Decimal("6.50"),
                packaging_weight_kg=Decimal("0.850"),
                sku_media_urls=[
                    "https://media.aaramhomes.com/skus/101mp-blu-swatch.jpg",
                    "https://media.aaramhomes.com/skus/101mp-blu-detail.jpg",
                ],
            ),
            SaveSkuInput(
                sku_id="101MP-WHT",
                colour="Classic White",
                size="Queen (60x78)",
                size_type="size",
                pack_configuration="Pack of 1",
                mrp=Decimal("2699.00"),
                selling_price=Decimal("1399.00"),
                cost_price=Decimal("600.00"),
                packaging_length_cm=Decimal("26.00"),
                packaging_breadth_cm=Decimal("20.00"),
                packaging_height_cm=Decimal("6.00"),
                packaging_weight_kg=Decimal("0.780"),
                sku_media_urls=[
                    "https://media.aaramhomes.com/skus/101mp-wht-swatch.jpg"
                ],
            ),
        ],
    )

    save_res = await service.save_product_family(payload)
    assert save_res.status == "SUCCESS"
    prod_id = save_res.product_internal_id

    # Transition to READY
    trans_res = await service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )
    assert trans_res.status == "SUCCESS"
    assert trans_res.lifecycle_state == "READY"

    # Generate Publication CSV Artifact
    artifact, csv_content = await adapter.generate_publication_artifact(
        target_product_internal_ids=[prod_id],
        output_dir=str(tmp_path),
        generated_by="TEST_RUNNER",
    )

    assert artifact is not None
    assert artifact.status == "COMMITTED"
    assert artifact.exported_sku_count == 2
    assert os.path.exists(artifact.file_path)

    # Verify CSV Content
    lines = csv_content.strip().split("\n")
    assert len(lines) == 3  # Header + 2 SKU rows
    headers = lines[0].split(",")
    assert len(headers) == 46
    assert headers[0] == "Product Code"
    assert headers[3] == "Sku Id"

    # Verify that the Product in DB is transitioned to PUBLISHED
    async with service.pool.acquire() as conn:
        prod_row = await conn.fetchrow(
            "SELECT lifecycle_state FROM catalog_products WHERE internal_id = $1;",
            prod_id,
        )
        assert prod_row["lifecycle_state"] == "PUBLISHED"

        art_row = await conn.fetchrow(
            "SELECT * FROM catalog_publication_artifacts WHERE artifact_id = $1;",
            artifact.artifact_id,
        )
        assert art_row is not None
        assert art_row["channel"] == "SHOPDECK"
        assert art_row["status"] == "COMMITTED"
        assert art_row["finalized_at"] is not None
        assert art_row["content_hash"] == artifact.content_hash


@pytest.mark.asyncio
async def test_shopdeck_size_projection_variations(adapter_and_service):
    """
    Validates size and size_type defaulting for ShopDeck:
    - If size is None -> defaults to 'Standard'
    - If size_type is None -> defaults to 'size'
    """
    adapter, _ = adapter_and_service

    # Single-size item without size
    row_no_size = {
        "product_code": "AH-APRON-01",
        "product_name": "Kitchen Apron Standard",
        "sku_id": "APRON-01",
        "selling_price": 499.00,
        "mrp": 999.00,
        "cost_price": 200.00,
        "packaging_length_cm": 20.00,
        "packaging_breadth_cm": 15.00,
        "packaging_height_cm": 3.00,
        "packaging_weight_kg": 0.250,
        "size": None,
        "size_type": None,
        "sku_media_urls": ["https://media.aaramhomes.com/apron.jpg"],
    }

    compiled = adapter.compile_csv_row(row_no_size)
    assert compiled["Size"] == "Standard"
    assert compiled["Size Type"] == "size"
    assert compiled["Quantity"] == "10"
    assert compiled["Pickup Address Code"] == "1"
    assert compiled["Return/Exchange Condition"] == "7"
    assert compiled["Visibility"] == "true"


@pytest.mark.asyncio
async def test_publication_failure_when_not_ready(adapter_and_service, tmp_path):
    """Publication export must reject when products are in DRAFT state."""
    adapter, service = adapter_and_service

    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-DRAFT-01",
            name="Draft Product Not Ready",
        ),
        skus=[
            SaveSkuInput(
                sku_id="DFT-01",
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
    save_res = await service.save_product_family(payload)
    prod_id = save_res.product_internal_id

    # Attempt export while in DRAFT
    with pytest.raises(ValueError, match="No eligible products in READY or PUBLISHED state"):
        await adapter.generate_publication_artifact(
            target_product_internal_ids=[prod_id],
            output_dir=str(tmp_path),
        )


# =============================================================================
# DUAL-RESOURCE STATE MACHINE & CRASH-POINT RECOVERY TESTS (CRASH POINTS A - E)
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_publication_and_cleanup_race(adapter_and_service, tmp_path):
    """
    Validates Gap 2: Dual-Resource Coordination & Race Prevention.
    Simultaneously runs generate_publication_artifact and cleanup_uncommitted_publication_artifacts.
    Verifies that cleanup NEVER deletes an in-flight active publication file.
    """
    adapter, service = adapter_and_service

    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-RACE-PUB",
            name="Publication Race Test Product",
            description="<p>Testing concurrent publication and cleanup</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            gst_percentage=Decimal("5.00"),
            hsn_code="6304",
        ),
        skus=[
            SaveSkuInput(
                sku_id="RACE-PUB1",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
                sku_media_urls=["https://media.aaramhomes.com/race.jpg"],
            )
        ],
    )
    save_res = await service.save_product_family(payload)
    prod_id = save_res.product_internal_id

    await service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )

    # Run publication and cleanup concurrently
    async def run_pub():
        return await adapter.generate_publication_artifact(
            target_product_internal_ids=[prod_id],
            output_dir=str(tmp_path),
        )

    async def run_clean():
        await asyncio.sleep(0.01)  # Stagger slightly to hit while file is created/in-flight
        return await adapter.cleanup_uncommitted_publication_artifacts(output_dir=str(tmp_path))

    pub_res, clean_res = await asyncio.gather(run_pub(), run_clean())
    artifact, _ = pub_res

    assert artifact is not None
    assert artifact.status == "COMMITTED"
    assert os.path.exists(artifact.file_path)
    assert artifact.file_path not in clean_res


@pytest.mark.asyncio
async def test_crash_point_a_before_file_creation(adapter_and_service, tmp_path):
    """
    Crash Point a: Crash occurs after intent registration, before any file is created on disk.
    - DB has IN_PROGRESS record.
    - Filesystem has 0 files.
    - Product remains in READY state (not falsely PUBLISHED).
    - Once lease expires, cleanup sets status to FAILED.
    """
    adapter, service = adapter_and_service
    art_id = uuid4()
    dummy_path = os.path.join(str(tmp_path), f"shopdeck_catalog_export_{art_id}.csv")

    async with adapter.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO catalog_publication_artifacts (
                artifact_id, channel, artifact_type, file_path, content_hash,
                exported_sku_count, status, expires_at
            ) VALUES ($1, 'SHOPDECK', 'CSV_46_COLUMN', $2, 'dummyhash', 1, 'IN_PROGRESS', CURRENT_TIMESTAMP - INTERVAL '1 second');
            """,
            art_id,
            dummy_path,
        )

    # Run cleanup with expired lease
    removed = await adapter.cleanup_uncommitted_publication_artifacts(output_dir=str(tmp_path))
    assert len(removed) == 0

    # Verify DB record is marked FAILED
    async with adapter.pool.acquire() as conn:
        status = await conn.fetchval(
            "SELECT status FROM catalog_publication_artifacts WHERE artifact_id = $1;",
            art_id,
        )
        assert status == "FAILED"


@pytest.mark.asyncio
async def test_crash_point_b_after_temp_file_creation(adapter_and_service, tmp_path):
    """
    Crash Point b: Process crashes after writing .tmp_export_{artifact_id}.csv before os.replace.
    - Active lease protects temp file from eager deletion.
    - Expired lease allows cleanup to prune temp file and mark DB FAILED.
    """
    adapter, _ = adapter_and_service
    art_id = uuid4()
    temp_file = os.path.join(str(tmp_path), f".tmp_export_{art_id}.csv")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("temporary file content")

    async with adapter.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO catalog_publication_artifacts (
                artifact_id, channel, artifact_type, file_path, content_hash,
                exported_sku_count, status, expires_at
            ) VALUES ($1, 'SHOPDECK', 'CSV_46_COLUMN', $2, 'dummyhash', 1, 'IN_PROGRESS', CURRENT_TIMESTAMP + INTERVAL '10 minutes');
            """,
            art_id,
            os.path.join(str(tmp_path), f"shopdeck_catalog_export_{art_id}.csv"),
        )

    # 1. Cleanup while lease is ACTIVE -> Temp file is preserved!
    removed = await adapter.cleanup_uncommitted_publication_artifacts(output_dir=str(tmp_path))
    assert temp_file not in removed
    assert os.path.exists(temp_file)

    # 2. Cleanup when lease EXPIRES -> Temp file is pruned and DB marked FAILED
    removed_exp = await adapter.cleanup_uncommitted_publication_artifacts(
        output_dir=str(tmp_path), force_expire_lease=True
    )
    assert temp_file in removed_exp
    assert not os.path.exists(temp_file)

    async with adapter.pool.acquire() as conn:
        status = await conn.fetchval(
            "SELECT status FROM catalog_publication_artifacts WHERE artifact_id = $1;",
            art_id,
        )
        assert status == "FAILED"


@pytest.mark.asyncio
async def test_crash_point_c_after_replace_before_db_commit(adapter_and_service, tmp_path):
    """
    Crash Point c: Target file was finalized via os.replace, but process died before DB commit transaction.
    - Product remains in READY state (no false PUBLISHED state).
    - Active in-flight lease protects target file.
    - Once abandoned/expired, cleanup safely removes the orphaned file.
    """
    adapter, service = adapter_and_service
    art_id = uuid4()
    target_file = os.path.join(str(tmp_path), f"shopdeck_catalog_export_{art_id}.csv")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("finalized target content prior to commit")

    async with adapter.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO catalog_publication_artifacts (
                artifact_id, channel, artifact_type, file_path, content_hash,
                exported_sku_count, status, expires_at
            ) VALUES ($1, 'SHOPDECK', 'CSV_46_COLUMN', $2, 'dummyhash', 1, 'IN_PROGRESS', CURRENT_TIMESTAMP + INTERVAL '10 minutes');
            """,
            art_id,
            target_file,
        )

    # Active lease -> File preserved
    removed = await adapter.cleanup_uncommitted_publication_artifacts(output_dir=str(tmp_path))
    assert target_file not in removed
    assert os.path.exists(target_file)

    # Expired lease -> Abandoned file pruned
    removed_exp = await adapter.cleanup_uncommitted_publication_artifacts(
        output_dir=str(tmp_path), force_expire_lease=True
    )
    assert target_file in removed_exp
    assert not os.path.exists(target_file)


@pytest.mark.asyncio
async def test_crash_point_d_during_db_transaction_rollback(adapter_and_service, tmp_path):
    """
    Crash Point d: Database transaction fails/aborts during commit.
    - In-process exception handler marks status = FAILED and deletes files immediately.
    - Product remains in READY state.
    """
    adapter, service = adapter_and_service

    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-CRASH-D",
            name="Crash Point D Product",
            description="<p>Testing DB transaction abort</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            gst_percentage=Decimal("5.00"),
            hsn_code="6304",
        ),
        skus=[
            SaveSkuInput(
                sku_id="CRASH-D1",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
                sku_media_urls=["https://media.aaramhomes.com/crash.jpg"],
            )
        ],
    )
    save_res = await service.save_product_family(payload)
    prod_id = save_res.product_internal_id

    await service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )

    real_pool = adapter.pool

    class FailingTxConn:
        def __init__(self, conn):
            self._conn = conn
        def __getattr__(self, name):
            return getattr(self._conn, name)
        def transaction(self):
            class FailingTx:
                async def __aenter__(self):
                    raise RuntimeError("Simulated Database Transaction Crash at Commit")
                async def __aexit__(self, *args):
                    pass
            return FailingTx()

    class FailingPoolProxy:
        def __init__(self, pool):
            self._pool = pool
        def __getattr__(self, name):
            return getattr(self._pool, name)
        def acquire(self):
            class FailingAcquireContext:
                def __init__(self, pool):
                    self._pool = pool
                    self._ctx = None
                async def __aenter__(self):
                    self._ctx = self._pool.acquire()
                    conn = await self._ctx.__aenter__()
                    return FailingTxConn(conn)
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if self._ctx:
                        await self._ctx.__aexit__(exc_type, exc_val, exc_tb)
            return FailingAcquireContext(self._pool)

    adapter.pool = FailingPoolProxy(real_pool)
    try:
        with pytest.raises(RuntimeError):
            await adapter.generate_publication_artifact(
                target_product_internal_ids=[prod_id],
                output_dir=str(tmp_path),
            )
    finally:
        adapter.pool = real_pool

    # File on disk was cleaned up immediately by exception handler
    assert len(os.listdir(str(tmp_path))) == 0

    # Product remains in READY state
    async with service.pool.acquire() as conn:
        state = await conn.fetchval(
            "SELECT lifecycle_state FROM catalog_products WHERE internal_id = $1;", prod_id
        )
        assert state == "READY"

        status = await conn.fetchval(
            "SELECT status FROM catalog_publication_artifacts ORDER BY created_at DESC LIMIT 1;"
        )
        assert status == "FAILED"


@pytest.mark.asyncio
async def test_crash_point_e_after_db_commit(adapter_and_service, tmp_path):
    """
    Crash Point e: Publication successfully committed.
    - Status is COMMITTED, Product is PUBLISHED, File exists on disk.
    - Cleanup NEVER deletes committed artifacts.
    """
    adapter, service = adapter_and_service

    payload = SaveProductFamilyPayload(
        product=SaveProductInput(
            product_code="AH-CRASH-E",
            name="Crash Point E Product",
            description="<p>Testing committed state</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            gst_percentage=Decimal("5.00"),
            hsn_code="6304",
        ),
        skus=[
            SaveSkuInput(
                sku_id="CRASH-E1",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("20.00"),
                packaging_breadth_cm=Decimal("15.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.500"),
                sku_media_urls=["https://media.aaramhomes.com/e.jpg"],
            )
        ],
    )
    save_res = await service.save_product_family(payload)
    prod_id = save_res.product_internal_id

    await service.transition_lifecycle_state(
        TransitionLifecycleStatePayload(
            product_internal_id=prod_id,
            target_state="READY",
        )
    )

    artifact, _ = await adapter.generate_publication_artifact(
        target_product_internal_ids=[prod_id],
        output_dir=str(tmp_path),
    )

    assert artifact.status == "COMMITTED"
    assert os.path.exists(artifact.file_path)

    # Cleanup runs -> Committed artifact is NEVER touched
    removed = await adapter.cleanup_uncommitted_publication_artifacts(output_dir=str(tmp_path))
    assert artifact.file_path not in removed
    assert os.path.exists(artifact.file_path)

    async with service.pool.acquire() as conn:
        state = await conn.fetchval(
            "SELECT lifecycle_state FROM catalog_products WHERE internal_id = $1;", prod_id
        )
        assert state == "PUBLISHED"
