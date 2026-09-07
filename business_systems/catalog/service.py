"""
Core Catalog Business System Service Layer
Implements authoritative mutation contracts, persistent concurrency-safe idempotency,
aggregate-wide readiness gates, and SKU resolution.
Strictly conforms to documents 03-catalog-business-rules.md, 04-catalog-contracts.md, and 06-catalog-data-schema.md.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import asyncpg

from .config import CATALOG_DATABASE_URL, IDEMPOTENCY_TTL_SECONDS
from .models import (
    MutationResponse,
    PriceHistoryEntity,
    ProductEntity,
    RenameProductCodePayload,
    SKUEntity,
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
    TransitionLifecycleStatePayload,
    ValidationErrorDetail,
    ValidationReport,
)
from .validation import (
    validate_product_code,
    validate_product_family_payload,
    validate_readiness_gate,
    validate_sku_id,
)


def _compute_request_hash(data: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 digest of an inbound payload."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class CatalogService:
    """Authoritative service interface for Catalog Business System operations."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def create(cls, database_url: str = CATALOG_DATABASE_URL) -> "CatalogService":
        """Factory method to initialize CatalogService with an asyncpg connection pool."""
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        return cls(pool)

    async def close(self):
        """Closes the underlying database connection pool."""
        await self.pool.close()

    # =========================================================================
    # 1. IDEMPOTENCY PERSISTENCE & CONCURRENCY CONTROL
    # =========================================================================

    async def _check_idempotency(
        self, conn: asyncpg.Connection, key: str, operation: str, req_hash: str
    ) -> Optional[MutationResponse]:
        """Checks for an unexpired cached response for a given idempotency key."""
        row = await conn.fetchrow(
            """
            SELECT operation, request_hash, response_payload, expires_at
            FROM catalog_idempotency_records
            WHERE idempotency_key = $1;
            """,
            key,
        )
        if not row:
            return None

        # Check if record is still valid (not expired)
        now = datetime.now(timezone.utc)
        expires_at = row["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now > expires_at:
            # Expired, allow re-execution
            return None

        if row["operation"] != operation or row["request_hash"] != req_hash:
            # Conflicting operation or payload for same idempotency key
            return MutationResponse(
                status="REJECTED",
                operation="IdempotencyCheck",
                errors=[
                    ValidationErrorDetail(
                        error_code="IDEMPOTENCY_CONFLICT",
                        target_entity="PAYLOAD",
                        target_field="idempotency_key",
                        rejected_value=key,
                        message=f"Idempotency key '{key}' provided with conflicting payload or operation.",
                    )
                ],
            )

        payload_dict = json.loads(row["response_payload"]) if isinstance(row["response_payload"], str) else row["response_payload"]
        resp = MutationResponse(**payload_dict)
        resp.status = "UNCHANGED_IDEMPOTENT"
        return resp

    async def _save_idempotency(
        self,
        conn: asyncpg.Connection,
        key: str,
        operation: str,
        req_hash: str,
        response: MutationResponse,
    ):
        """Persists the mutation response with configured TTL."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_at = now + timedelta(seconds=IDEMPOTENCY_TTL_SECONDS)
        resp_json = response.model_dump_json()

        await conn.execute(
            """
            INSERT INTO catalog_idempotency_records (
                idempotency_key, operation, request_hash, response_payload, created_at, expires_at
            ) VALUES ($1, $2, $3, $4::jsonb, $5, $6)
            ON CONFLICT (idempotency_key) DO UPDATE SET
                operation = EXCLUDED.operation,
                request_hash = EXCLUDED.request_hash,
                response_payload = EXCLUDED.response_payload,
                created_at = EXCLUDED.created_at,
                expires_at = EXCLUDED.expires_at;
            """,
            key,
            operation,
            req_hash,
            resp_json,
            now,
            expires_at,
        )

    async def cleanup_expired_idempotency_records(self) -> int:
        """Physically deletes expired idempotency records from the database."""
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM catalog_idempotency_records WHERE expires_at < CURRENT_TIMESTAMP;"
            )
            count = int(res.split(" ")[-1]) if " " in res else 0
            return count

    # =========================================================================
    # 2. SAVE PRODUCT FAMILY MUTATION CONTRACT
    # =========================================================================

    async def save_product_family(
        self, payload: SaveProductFamilyPayload
    ) -> MutationResponse:
        """
        Atomically creates or updates a Product family and its sibling SKUs.
        Enforces deterministic business rules, strict parent membership, aggregate readiness,
        and price history ledgering.
        """
        req_dict = payload.model_dump()
        req_hash = _compute_request_hash(req_dict)

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Concurrency-safe atomic reservation via PostgreSQL transaction-level advisory lock
                    if payload.idempotency_key:
                        await conn.execute(
                            "SELECT pg_advisory_xact_lock(hashtext($1));",
                            f"catalog_idem:{payload.idempotency_key}",
                        )
                        cached = await self._check_idempotency(
                            conn, payload.idempotency_key, "SaveProductFamily", req_hash
                        )
                        if cached:
                            return cached

                    # Syntax and Domain Invariant Validation on payload
                    val_report = validate_product_family_payload(payload)
                    if not val_report.is_valid:
                        return MutationResponse(
                            status="REJECTED",
                            operation="SaveProductFamily",
                            product_code=payload.product.product_code,
                            warnings=val_report.warnings,
                            errors=val_report.errors,
                        )

                    prod_in = payload.product

                    # Product Existence Verification
                    existing_prod = None
                    if prod_in.product_internal_id:
                        existing_prod = await conn.fetchrow(
                            "SELECT * FROM catalog_products WHERE internal_id = $1;",
                            prod_in.product_internal_id,
                        )
                        if not existing_prod:
                            return MutationResponse(
                                status="REJECTED",
                                operation="SaveProductFamily",
                                errors=[
                                    ValidationErrorDetail(
                                        error_code="PRODUCT_NOT_FOUND",
                                        target_entity="PRODUCT",
                                        target_field="product_internal_id",
                                        rejected_value=str(prod_in.product_internal_id),
                                        message=f"Product with internal_id '{prod_in.product_internal_id}' does not exist.",
                                    )
                                ],
                            )

                    prod_internal_id = prod_in.product_internal_id or (existing_prod["internal_id"] if existing_prod else uuid4())

                    # Check product_code uniqueness & permanent historical reservation (Rule PRD-05 / ADR-RUL-008)
                    code_res = await conn.fetchrow(
                        "SELECT product_internal_id FROM catalog_product_code_reservations WHERE product_code = $1;",
                        prod_in.product_code,
                    )
                    if code_res and code_res["product_internal_id"] != prod_internal_id:
                        return MutationResponse(
                            status="REJECTED",
                            operation="SaveProductFamily",
                            product_code=prod_in.product_code,
                            errors=[
                                ValidationErrorDetail(
                                    error_code="PRODUCT_CODE_COLLISION",
                                    target_entity="PRODUCT",
                                    target_field="product_code",
                                    rejected_value=prod_in.product_code,
                                    message=f"Product Code '{prod_in.product_code}' is permanently reserved for Product entity '{code_res['product_internal_id']}' and cannot be recycled (Rule PRD-05 / ADR-RUL-008).",
                                )
                            ],
                        )

                    # Check SKU ID uniqueness, strict Parent-Product membership, and permanent historical reservations (Rule RET-02 / ADR-RUL-002)
                    for sku_in in payload.skus:
                        # 1. Verify sku_internal_id parent membership if provided
                        if sku_in.sku_internal_id:
                            sku_by_id = await conn.fetchrow(
                                "SELECT internal_id, product_internal_id, sku_id FROM catalog_skus WHERE internal_id = $1;",
                                sku_in.sku_internal_id,
                            )
                            if sku_by_id and sku_by_id["product_internal_id"] != prod_internal_id:
                                return MutationResponse(
                                    status="REJECTED",
                                    operation="SaveProductFamily",
                                    product_code=prod_in.product_code,
                                    errors=[
                                        ValidationErrorDetail(
                                            error_code="CROSS_PRODUCT_SKU_MUTATION_DENIED",
                                            target_entity="SKU",
                                            target_field="sku_internal_id",
                                            rejected_value=str(sku_in.sku_internal_id),
                                            message=f"SKU with internal_id '{sku_in.sku_internal_id}' belongs to a different Product family ({sku_by_id['product_internal_id']}) and cannot be mutated under Product '{prod_internal_id}'.",
                                        )
                                    ],
                                )

                        # 2. Verify permanent historical sku_id reservation
                        sku_res = await conn.fetchrow(
                            """
                            SELECT r.sku_internal_id, s.product_internal_id, s.sku_id AS current_sku_id
                            FROM catalog_sku_id_reservations r
                            LEFT JOIN catalog_skus s ON r.sku_internal_id = s.internal_id
                            WHERE r.sku_id = $1;
                            """,
                            sku_in.sku_id,
                        )
                        if sku_res:
                            reserved_sku_id = sku_res["sku_internal_id"]
                            reserved_prod_id = sku_res["product_internal_id"]
                            current_sku_id = sku_res["current_sku_id"]

                            # Case A: If target sku_internal_id was provided, it must match the reserved entity
                            if sku_in.sku_internal_id:
                                if sku_in.sku_internal_id != reserved_sku_id:
                                    return MutationResponse(
                                        status="REJECTED",
                                        operation="SaveProductFamily",
                                        product_code=prod_in.product_code,
                                        errors=[
                                            ValidationErrorDetail(
                                                error_code="SKU_COLLISION",
                                                target_entity="SKU",
                                                target_field="sku_id",
                                                rejected_value=sku_in.sku_id,
                                                message=f"SKU ID '{sku_in.sku_id}' is permanently reserved for another SKU entity ({reserved_sku_id}) and cannot be recycled (Rule RET-02).",
                                            )
                                        ],
                                    )
                            # Case B: If target sku_internal_id was not provided
                            else:
                                if reserved_prod_id and reserved_prod_id != prod_internal_id:
                                    return MutationResponse(
                                        status="REJECTED",
                                        operation="SaveProductFamily",
                                        product_code=prod_in.product_code,
                                        errors=[
                                            ValidationErrorDetail(
                                                error_code="CROSS_PRODUCT_SKU_MUTATION_DENIED",
                                                target_entity="SKU",
                                                target_field="sku_id",
                                                rejected_value=sku_in.sku_id,
                                                message=f"SKU ID '{sku_in.sku_id}' belongs to another Product family ({reserved_prod_id}) and cannot be hijacked.",
                                            )
                                        ],
                                    )
                                elif current_sku_id and current_sku_id != sku_in.sku_id:
                                    # The entity was previously named sku_in.sku_id, but has since been renamed!
                                    # Reusing this historical retired key for a new SKU creation is strictly prohibited.
                                    return MutationResponse(
                                        status="REJECTED",
                                        operation="SaveProductFamily",
                                        product_code=prod_in.product_code,
                                        errors=[
                                            ValidationErrorDetail(
                                                error_code="SKU_COLLISION",
                                                target_entity="SKU",
                                                target_field="sku_id",
                                                rejected_value=sku_in.sku_id,
                                                message=f"SKU ID '{sku_in.sku_id}' is a retired historical key permanently reserved for SKU entity '{reserved_sku_id}' and cannot be recycled for a new SKU (Rule RET-02).",
                                            )
                                        ],
                                    )
                                else:
                                    # Match existing SKU in this product family
                                    sku_in.sku_internal_id = reserved_sku_id

                    # Aggregate Attribute Merging:
                    # Merge existing product attributes if partial payload is supplied
                    if existing_prod:
                        updated_name = prod_in.name if prod_in.name is not None else existing_prod["name"]
                        updated_desc = prod_in.description if prod_in.description is not None else existing_prod["description"]
                        updated_ptype = prod_in.product_type if prod_in.product_type is not None else existing_prod["product_type"]
                        updated_brand = prod_in.brand if prod_in.brand is not None else existing_prod["brand"]
                        updated_hsn = prod_in.hsn_code if prod_in.hsn_code is not None else existing_prod["hsn_code"]
                        updated_gst = prod_in.gst_percentage if prod_in.gst_percentage is not None else existing_prod["gst_percentage"]
                        updated_fabric = prod_in.fabric_type if prod_in.fabric_type is not None else existing_prod["fabric_type"]
                        updated_care = prod_in.care_instructions if prod_in.care_instructions is not None else existing_prod["care_instructions"]
                        updated_set = prod_in.set_composition if prod_in.set_composition is not None else existing_prod["set_composition"]
                        updated_pmedia = prod_in.product_media_urls if prod_in.product_media_urls else (json.loads(existing_prod["product_media_urls"]) if isinstance(existing_prod["product_media_urls"], str) else (existing_prod["product_media_urls"] or []))
                        updated_chart = prod_in.size_chart_url if prod_in.size_chart_url is not None else existing_prod["size_chart_url"]
                        updated_video = prod_in.video_urls if prod_in.video_urls else (json.loads(existing_prod["video_urls"]) if isinstance(existing_prod["video_urls"], str) else (existing_prod["video_urls"] or []))
                        updated_tags = prod_in.collection_tags if prod_in.collection_tags else (existing_prod["collection_tags"] or [])
                    else:
                        updated_name = prod_in.name
                        updated_desc = prod_in.description
                        updated_ptype = prod_in.product_type
                        updated_brand = prod_in.brand
                        updated_hsn = prod_in.hsn_code
                        updated_gst = prod_in.gst_percentage
                        updated_fabric = prod_in.fabric_type
                        updated_care = prod_in.care_instructions
                        updated_set = prod_in.set_composition
                        updated_pmedia = prod_in.product_media_urls
                        updated_chart = prod_in.size_chart_url
                        updated_video = prod_in.video_urls
                        updated_tags = prod_in.collection_tags

                    full_prod_for_gate = SaveProductInput(
                        product_internal_id=prod_internal_id,
                        product_code=prod_in.product_code,
                        name=updated_name,
                        description=updated_desc,
                        product_type=updated_ptype,
                        brand=updated_brand,
                        hsn_code=updated_hsn,
                        gst_percentage=updated_gst,
                        fabric_type=updated_fabric,
                        care_instructions=updated_care,
                        set_composition=updated_set,
                        product_media_urls=updated_pmedia,
                        size_chart_url=updated_chart,
                        video_urls=updated_video,
                        collection_tags=updated_tags,
                    )

                    # Fetch all existing persisted sibling SKUs to evaluate complete family aggregate
                    existing_skus_map: Dict[str, SaveSkuInput] = {}
                    if existing_prod:
                        db_skus = await conn.fetch(
                            "SELECT * FROM catalog_skus WHERE product_internal_id = $1;",
                            prod_internal_id,
                        )
                        for r in db_skus:
                            existing_skus_map[r["sku_id"]] = SaveSkuInput(
                                sku_internal_id=r["internal_id"],
                                sku_id=r["sku_id"],
                                colour=r["colour"],
                                size=r["size"],
                                size_type=r["size_type"],
                                pack_configuration=r["pack_configuration"],
                                mrp=r["mrp"],
                                selling_price=r["selling_price"],
                                cost_price=r["cost_price"],
                                packaging_length_cm=r["packaging_length_cm"],
                                packaging_breadth_cm=r["packaging_breadth_cm"],
                                packaging_height_cm=r["packaging_height_cm"],
                                packaging_weight_kg=r["packaging_weight_kg"],
                                sku_media_urls=json.loads(r["sku_media_urls"]) if isinstance(r["sku_media_urls"], str) else (r["sku_media_urls"] or []),
                            )

                    # Merge payload SKUs into aggregate map
                    for s in payload.skus:
                        if s.sku_id in existing_skus_map:
                            prev = existing_skus_map[s.sku_id]
                            merged_s = SaveSkuInput(
                                sku_internal_id=prev.sku_internal_id or s.sku_internal_id,
                                sku_id=s.sku_id,
                                colour=s.colour if s.colour is not None else prev.colour,
                                size=s.size if s.size is not None else prev.size,
                                size_type=s.size_type if s.size_type is not None else prev.size_type,
                                pack_configuration=s.pack_configuration if s.pack_configuration is not None else prev.pack_configuration,
                                mrp=s.mrp if s.mrp is not None else prev.mrp,
                                selling_price=s.selling_price if s.selling_price is not None else prev.selling_price,
                                cost_price=s.cost_price if s.cost_price is not None else prev.cost_price,
                                packaging_length_cm=s.packaging_length_cm if s.packaging_length_cm is not None else prev.packaging_length_cm,
                                packaging_breadth_cm=s.packaging_breadth_cm if s.packaging_breadth_cm is not None else prev.packaging_breadth_cm,
                                packaging_height_cm=s.packaging_height_cm if s.packaging_height_cm is not None else prev.packaging_height_cm,
                                packaging_weight_kg=s.packaging_weight_kg if s.packaging_weight_kg is not None else prev.packaging_weight_kg,
                                sku_media_urls=s.sku_media_urls if s.sku_media_urls else prev.sku_media_urls,
                            )
                            existing_skus_map[s.sku_id] = merged_s
                        else:
                            existing_skus_map[s.sku_id] = s

                    full_family_skus = list(existing_skus_map.values())

                    # Determine Lifecycle State on Mutation
                    current_state = existing_prod["lifecycle_state"] if existing_prod else "DRAFT"
                    new_lifecycle_state = current_state

                    if not existing_prod:
                        new_lifecycle_state = "DRAFT"
                    elif current_state in ("PUBLISHED", "READY"):
                        gate_report = validate_readiness_gate(full_prod_for_gate, full_family_skus)
                        new_lifecycle_state = "READY" if gate_report.is_valid else "DRAFT"

                    # Persist Product Record
                    if not existing_prod:
                        await conn.execute(
                            """
                            INSERT INTO catalog_products (
                                internal_id, product_code, name, description, product_type, brand,
                                hsn_code, gst_percentage, fabric_type, care_instructions, set_composition,
                                product_media_urls, size_chart_url, video_urls, collection_tags, lifecycle_state
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13, $14::jsonb, $15, $16
                            );
                            """,
                            prod_internal_id,
                            prod_in.product_code,
                            updated_name,
                            updated_desc,
                            updated_ptype,
                            updated_brand,
                            updated_hsn,
                            updated_gst,
                            updated_fabric,
                            updated_care,
                            updated_set,
                            json.dumps(updated_pmedia),
                            updated_chart,
                            json.dumps(updated_video),
                            updated_tags,
                            new_lifecycle_state,
                        )
                    else:
                        await conn.execute(
                            """
                            UPDATE catalog_products SET
                                product_code = $2,
                                name = $3,
                                description = $4,
                                product_type = $5,
                                brand = $6,
                                hsn_code = $7,
                                gst_percentage = $8,
                                fabric_type = $9,
                                care_instructions = $10,
                                set_composition = $11,
                                product_media_urls = $12::jsonb,
                                size_chart_url = $13,
                                video_urls = $14::jsonb,
                                collection_tags = $15,
                                lifecycle_state = $16
                            WHERE internal_id = $1;
                            """,
                            prod_internal_id,
                            prod_in.product_code,
                            updated_name,
                            updated_desc,
                            updated_ptype,
                            updated_brand,
                            updated_hsn,
                            updated_gst,
                            updated_fabric,
                            updated_care,
                            updated_set,
                            json.dumps(updated_pmedia),
                            updated_chart,
                            json.dumps(updated_video),
                            updated_tags,
                            new_lifecycle_state,
                        )

                    # Persist Sibling SKUs & Record Price History
                    saved_sku_ids: List[UUID] = []
                    for sku_in in payload.skus:
                        existing_sku = None
                        sku_internal_id = sku_in.sku_internal_id or uuid4()
                        if sku_in.sku_internal_id:
                            existing_sku = await conn.fetchrow(
                                "SELECT * FROM catalog_skus WHERE internal_id = $1;",
                                sku_in.sku_internal_id,
                            )

                        if not existing_sku:
                            # Insert New SKU
                            await conn.execute(
                                """
                                INSERT INTO catalog_skus (
                                    internal_id, product_internal_id, sku_id, colour, size, size_type,
                                    pack_configuration, mrp, selling_price, cost_price,
                                    packaging_length_cm, packaging_breadth_cm, packaging_height_cm,
                                    packaging_weight_kg, sku_media_urls
                                ) VALUES (
                                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15::jsonb
                                );
                                """,
                                sku_internal_id,
                                prod_internal_id,
                                sku_in.sku_id,
                                sku_in.colour,
                                sku_in.size,
                                sku_in.size_type,
                                sku_in.pack_configuration,
                                sku_in.mrp,
                                sku_in.selling_price,
                                sku_in.cost_price,
                                sku_in.packaging_length_cm,
                                sku_in.packaging_breadth_cm,
                                sku_in.packaging_height_cm,
                                sku_in.packaging_weight_kg,
                                json.dumps(sku_in.sku_media_urls),
                            )
                            # Record initial price history
                            await conn.execute(
                                """
                                INSERT INTO catalog_price_history (
                                    sku_internal_id, previous_mrp, new_mrp, previous_selling_price, new_selling_price,
                                    previous_cost_price, new_cost_price, changed_by
                                ) VALUES ($1, NULL, $2, NULL, $3, NULL, $4, 'SYSTEM');
                                """,
                                sku_internal_id,
                                sku_in.mrp,
                                sku_in.selling_price,
                                sku_in.cost_price,
                            )
                        else:
                            sku_colour = sku_in.colour if sku_in.colour is not None else existing_sku["colour"]
                            sku_size = sku_in.size if sku_in.size is not None else existing_sku["size"]
                            sku_stype = sku_in.size_type if sku_in.size_type is not None else existing_sku["size_type"]
                            sku_pack = sku_in.pack_configuration if sku_in.pack_configuration is not None else existing_sku["pack_configuration"]
                            sku_mrp = sku_in.mrp if sku_in.mrp is not None else existing_sku["mrp"]
                            sku_sell = sku_in.selling_price if sku_in.selling_price is not None else existing_sku["selling_price"]
                            sku_cost = sku_in.cost_price if sku_in.cost_price is not None else existing_sku["cost_price"]
                            sku_l = sku_in.packaging_length_cm if sku_in.packaging_length_cm is not None else existing_sku["packaging_length_cm"]
                            sku_b = sku_in.packaging_breadth_cm if sku_in.packaging_breadth_cm is not None else existing_sku["packaging_breadth_cm"]
                            sku_h = sku_in.packaging_height_cm if sku_in.packaging_height_cm is not None else existing_sku["packaging_height_cm"]
                            sku_w = sku_in.packaging_weight_kg if sku_in.packaging_weight_kg is not None else existing_sku["packaging_weight_kg"]
                            sku_media = sku_in.sku_media_urls if sku_in.sku_media_urls else (json.loads(existing_sku["sku_media_urls"]) if isinstance(existing_sku["sku_media_urls"], str) else (existing_sku["sku_media_urls"] or []))

                            # Check for price changes
                            price_changed = (
                                existing_sku["mrp"] != sku_mrp
                                or existing_sku["selling_price"] != sku_sell
                                or existing_sku["cost_price"] != sku_cost
                            )
                            if price_changed:
                                await conn.execute(
                                    """
                                    INSERT INTO catalog_price_history (
                                        sku_internal_id, previous_mrp, new_mrp, previous_selling_price, new_selling_price,
                                        previous_cost_price, new_cost_price, changed_by
                                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'SYSTEM');
                                    """,
                                    sku_internal_id,
                                    existing_sku["mrp"],
                                    sku_mrp,
                                    existing_sku["selling_price"],
                                    sku_sell,
                                    existing_sku["cost_price"],
                                    sku_cost,
                                )

                            # Update existing SKU
                            await conn.execute(
                                """
                                UPDATE catalog_skus SET
                                    sku_id = $2,
                                    colour = $3,
                                    size = $4,
                                    size_type = $5,
                                    pack_configuration = $6,
                                    mrp = $7,
                                    selling_price = $8,
                                    cost_price = $9,
                                    packaging_length_cm = $10,
                                    packaging_breadth_cm = $11,
                                    packaging_height_cm = $12,
                                    packaging_weight_kg = $13,
                                    sku_media_urls = $14::jsonb
                                WHERE internal_id = $1;
                                """,
                                sku_internal_id,
                                sku_in.sku_id,
                                sku_colour,
                                sku_size,
                                sku_stype,
                                sku_pack,
                                sku_mrp,
                                sku_sell,
                                sku_cost,
                                sku_l,
                                sku_b,
                                sku_h,
                                sku_w,
                                json.dumps(sku_media),
                            )

                        saved_sku_ids.append(sku_internal_id)

                    response = MutationResponse(
                        status="SUCCESS",
                        operation="SaveProductFamily",
                        product_internal_id=prod_internal_id,
                        product_code=prod_in.product_code,
                        lifecycle_state=new_lifecycle_state,
                        affected_sku_count=len(saved_sku_ids),
                        sku_internal_ids=saved_sku_ids,
                        warnings=val_report.warnings,
                    )

                    if payload.idempotency_key:
                        await self._save_idempotency(
                            conn,
                            payload.idempotency_key,
                            "SaveProductFamily",
                            req_hash,
                            response,
                        )

                    return response
        except (asyncpg.RaiseError, asyncpg.UniqueViolationError) as exc:
            msg = str(exc)
            if "SKU ID" in msg or "catalog_skus_sku_id" in msg or "catalog_sku_id_reservations" in msg:
                return MutationResponse(
                    status="REJECTED",
                    operation="SaveProductFamily",
                    errors=[
                        ValidationErrorDetail(
                            error_code="SKU_COLLISION",
                            target_entity="SKU",
                            target_field="sku_id",
                            message=f"Database reservation constraint rejected SKU: {msg}",
                        )
                    ],
                )
            elif "Product Code" in msg or "catalog_products_code" in msg or "catalog_product_code_reservations" in msg:
                return MutationResponse(
                    status="REJECTED",
                    operation="SaveProductFamily",
                    errors=[
                        ValidationErrorDetail(
                            error_code="PRODUCT_CODE_COLLISION",
                            target_entity="PRODUCT",
                            target_field="product_code",
                            message=f"Database reservation constraint rejected Product Code: {msg}",
                        )
                    ],
                )
            raise

    # =========================================================================
    # 3. RENAME PRODUCT CODE ACTION
    # =========================================================================

    async def rename_product_code(
        self, payload: RenameProductCodePayload
    ) -> MutationResponse:
        """Renames the commercial grouping code for an existing Product family."""
        req_dict = payload.model_dump()
        req_hash = _compute_request_hash(req_dict)

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    if payload.idempotency_key:
                        await conn.execute(
                            "SELECT pg_advisory_xact_lock(hashtext($1));",
                            f"catalog_idem:{payload.idempotency_key}",
                        )
                        cached = await self._check_idempotency(
                            conn, payload.idempotency_key, "RenameProductCode", req_hash
                        )
                        if cached:
                            return cached

                    err = validate_product_code(payload.new_product_code)
                    if err:
                        return MutationResponse(
                            status="REJECTED",
                            operation="RenameProductCode",
                            errors=[err],
                        )

                    prod = await conn.fetchrow(
                        "SELECT * FROM catalog_products WHERE internal_id = $1;",
                        payload.product_internal_id,
                    )
                    if not prod:
                        return MutationResponse(
                            status="REJECTED",
                            operation="RenameProductCode",
                            errors=[
                                ValidationErrorDetail(
                                    error_code="PRODUCT_NOT_FOUND",
                                    target_entity="PRODUCT",
                                    target_field="product_internal_id",
                                    rejected_value=str(payload.product_internal_id),
                                    message=f"Product with internal_id '{payload.product_internal_id}' does not exist.",
                                )
                            ],
                        )

                    code_res = await conn.fetchrow(
                        "SELECT product_internal_id FROM catalog_product_code_reservations WHERE product_code = $1;",
                        payload.new_product_code,
                    )
                    if code_res and code_res["product_internal_id"] != payload.product_internal_id:
                        return MutationResponse(
                            status="REJECTED",
                            operation="RenameProductCode",
                            errors=[
                                ValidationErrorDetail(
                                    error_code="PRODUCT_CODE_COLLISION",
                                    target_entity="PRODUCT",
                                    target_field="product_code",
                                    rejected_value=payload.new_product_code,
                                    message=f"Product Code '{payload.new_product_code}' is permanently reserved for Product entity '{code_res['product_internal_id']}' and cannot be recycled (Rule PRD-05 / ADR-RUL-008).",
                                )
                            ],
                        )

                    new_state = prod["lifecycle_state"]
                    if new_state == "PUBLISHED":
                        new_state = "READY"

                    await conn.execute(
                        """
                        UPDATE catalog_products
                        SET product_code = $2, lifecycle_state = $3
                        WHERE internal_id = $1;
                        """,
                        payload.product_internal_id,
                        payload.new_product_code,
                        new_state,
                    )

                    skus = await conn.fetch(
                        "SELECT internal_id FROM catalog_skus WHERE product_internal_id = $1;",
                        payload.product_internal_id,
                    )
                    sku_ids = [r["internal_id"] for r in skus]

                    response = MutationResponse(
                        status="SUCCESS",
                        operation="RenameProductCode",
                        product_internal_id=payload.product_internal_id,
                        product_code=payload.new_product_code,
                        lifecycle_state=new_state,
                        affected_sku_count=len(sku_ids),
                        sku_internal_ids=sku_ids,
                    )

                    if payload.idempotency_key:
                        await self._save_idempotency(
                            conn,
                            payload.idempotency_key,
                            "RenameProductCode",
                            req_hash,
                            response,
                        )

                    return response
        except (asyncpg.RaiseError, asyncpg.UniqueViolationError) as exc:
            msg = str(exc)
            if "Product Code" in msg or "catalog_products_code" in msg or "catalog_product_code_reservations" in msg:
                return MutationResponse(
                    status="REJECTED",
                    operation="RenameProductCode",
                    errors=[
                        ValidationErrorDetail(
                            error_code="PRODUCT_CODE_COLLISION",
                            target_entity="PRODUCT",
                            target_field="product_code",
                            rejected_value=payload.new_product_code,
                            message=f"Database reservation constraint rejected Product Code: {msg}",
                        )
                    ],
                )
            raise

    # =========================================================================
    # 4. TRANSITION LIFECYCLE STATE ACTION
    # =========================================================================

    async def transition_lifecycle_state(
        self, payload: TransitionLifecycleStatePayload
    ) -> MutationResponse:
        """Transitions a Product family between Catalog-owned states: DRAFT <-> READY."""
        req_dict = payload.model_dump()
        req_hash = _compute_request_hash(req_dict)

        if payload.target_state not in ("DRAFT", "READY"):
            return MutationResponse(
                status="REJECTED",
                operation="TransitionLifecycleState",
                errors=[
                    ValidationErrorDetail(
                        error_code="INVALID_LIFECYCLE_TRANSITION",
                        target_entity="PRODUCT",
                        target_field="target_state",
                        rejected_value=payload.target_state,
                        message="Direct manual transition is allowed only between 'DRAFT' and 'READY'. 'PUBLISHED' is achieved via publication artifact generation.",
                    )
                ],
            )

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if payload.idempotency_key:
                    await conn.execute(
                        "SELECT pg_advisory_xact_lock(hashtext($1));",
                        f"catalog_idem:{payload.idempotency_key}",
                    )
                    cached = await self._check_idempotency(
                        conn, payload.idempotency_key, "TransitionLifecycleState", req_hash
                    )
                    if cached:
                        return cached

                prod = await conn.fetchrow(
                    "SELECT * FROM catalog_products WHERE internal_id = $1;",
                    payload.product_internal_id,
                )
                if not prod:
                    return MutationResponse(
                        status="REJECTED",
                        operation="TransitionLifecycleState",
                        errors=[
                            ValidationErrorDetail(
                                error_code="PRODUCT_NOT_FOUND",
                                target_entity="PRODUCT",
                                target_field="product_internal_id",
                                rejected_value=str(payload.product_internal_id),
                                message=f"Product with internal_id '{payload.product_internal_id}' does not exist.",
                            )
                        ],
                    )

                if payload.target_state == "READY":
                    skus = await conn.fetch(
                        "SELECT * FROM catalog_skus WHERE product_internal_id = $1;",
                        payload.product_internal_id,
                    )
                    if not skus:
                        return MutationResponse(
                            status="REJECTED",
                            operation="TransitionLifecycleState",
                            product_internal_id=payload.product_internal_id,
                            product_code=prod["product_code"],
                            errors=[
                                ValidationErrorDetail(
                                    error_code="LIFECYCLE_COMPLETENESS_ERROR",
                                    target_entity="PRODUCT",
                                    target_field="skus",
                                    rejected_value="[]",
                                    message="Cannot transition Product to READY without at least one child SKU.",
                                )
                            ],
                        )

                    prod_input = SaveProductInput(
                        product_internal_id=prod["internal_id"],
                        product_code=prod["product_code"],
                        name=prod["name"],
                        description=prod["description"],
                        product_type=prod["product_type"],
                        brand=prod["brand"],
                        gst_percentage=prod["gst_percentage"],
                        hsn_code=prod["hsn_code"],
                        fabric_type=prod["fabric_type"],
                        care_instructions=prod["care_instructions"],
                        set_composition=prod["set_composition"],
                        product_media_urls=json.loads(prod["product_media_urls"]) if isinstance(prod["product_media_urls"], str) else (prod["product_media_urls"] or []),
                        size_chart_url=prod["size_chart_url"],
                        video_urls=json.loads(prod["video_urls"]) if isinstance(prod["video_urls"], str) else (prod["video_urls"] or []),
                        collection_tags=prod["collection_tags"] or [],
                    )
                    sku_inputs = [
                        SaveSkuInput(
                            sku_internal_id=s["internal_id"],
                            sku_id=s["sku_id"],
                            colour=s["colour"],
                            size=s["size"],
                            size_type=s["size_type"],
                            pack_configuration=s["pack_configuration"],
                            mrp=s["mrp"],
                            selling_price=s["selling_price"],
                            cost_price=s["cost_price"],
                            packaging_length_cm=s["packaging_length_cm"],
                            packaging_breadth_cm=s["packaging_breadth_cm"],
                            packaging_height_cm=s["packaging_height_cm"],
                            packaging_weight_kg=s["packaging_weight_kg"],
                            sku_media_urls=json.loads(s["sku_media_urls"]) if isinstance(s["sku_media_urls"], str) else (s["sku_media_urls"] or []),
                        )
                        for s in skus
                    ]
                    gate_report = validate_readiness_gate(prod_input, sku_inputs)
                    if not gate_report.is_valid:
                        return MutationResponse(
                            status="REJECTED",
                            operation="TransitionLifecycleState",
                            product_internal_id=payload.product_internal_id,
                            product_code=prod["product_code"],
                            errors=gate_report.errors,
                            warnings=gate_report.warnings,
                        )

                await conn.execute(
                    "UPDATE catalog_products SET lifecycle_state = $2 WHERE internal_id = $1;",
                    payload.product_internal_id,
                    payload.target_state,
                )

                response = MutationResponse(
                    status="SUCCESS",
                    operation="TransitionLifecycleState",
                    product_internal_id=payload.product_internal_id,
                    product_code=prod["product_code"],
                    lifecycle_state=payload.target_state,
                )

                if payload.idempotency_key:
                    await self._save_idempotency(
                        conn,
                        payload.idempotency_key,
                        "TransitionLifecycleState",
                        req_hash,
                        response,
                    )

                return response

    # =========================================================================
    # 5. DETERMINISTIC SKU RESOLUTION CONTRACT
    # =========================================================================

    async def resolve_sku(
        self, lookup_key: str, lookup_type: str = "AUTO"
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves a SKU deterministically across 3 lookup dimensions:
        1. sku_id (e.g. '126BS-BLU')
        2. shopdeck_sku_id (external token e.g. 'JVAZr4Qf')
        3. internal_id (UUID)
        """
        if not lookup_key or not isinstance(lookup_key, str):
            return None

        lookup_key = lookup_key.strip()
        async with self.pool.acquire() as conn:
            if lookup_type in ("AUTO", "UUID"):
                try:
                    uuid_val = UUID(lookup_key)
                    row = await conn.fetchrow(
                        "SELECT * FROM vw_catalog_master WHERE sku_internal_id = $1;",
                        uuid_val,
                    )
                    if row:
                        return dict(row)
                except ValueError:
                    pass

            if lookup_type in ("AUTO", "SKU_ID"):
                row = await conn.fetchrow(
                    "SELECT * FROM vw_catalog_master WHERE sku_id = $1;",
                    lookup_key.upper(),
                )
                if row:
                    return dict(row)
                # Fallback to historical SKU reservation registry (Rule RET-02)
                hist_res = await conn.fetchrow(
                    "SELECT sku_internal_id FROM catalog_sku_id_reservations WHERE sku_id = $1;",
                    lookup_key.upper(),
                )
                if hist_res:
                    row = await conn.fetchrow(
                        "SELECT * FROM vw_catalog_master WHERE sku_internal_id = $1;",
                        hist_res["sku_internal_id"],
                    )
                    if row:
                        return dict(row)

            if lookup_type in ("AUTO", "CHANNEL_TOKEN"):
                row = await conn.fetchrow(
                    "SELECT * FROM vw_catalog_master WHERE shopdeck_sku_id = $1;",
                    lookup_key,
                )
                if row:
                    return dict(row)

        return None

    # =========================================================================
    # 6. PUBLICATION ARTIFACT GENERATION
    # =========================================================================

    async def generate_channel_publication_artifact(
        self, channel: str = "SHOPDECK"
    ) -> MutationResponse:
        """
        Delegates to the specific channel adapter to compile the publication artifact.
        Currently only supports SHOPDECK.
        """
        if channel != "SHOPDECK":
            return MutationResponse(
                status="REJECTED",
                operation="GenerateChannelPublicationArtifact",
                errors=[
                    ValidationErrorDetail(
                        error_code="UNSUPPORTED_CHANNEL",
                        target_entity="CHANNEL",
                        target_field="channel",
                        rejected_value=channel,
                        message=f"Channel {channel} is not supported for publication.",
                    )
                ]
            )

        from .shopdeck_adapter import ShopDeckAdapter

        adapter = ShopDeckAdapter(self.pool)
        try:
            artifact, _ = await adapter.generate_publication_artifact(generated_by="SYSTEM")
            return MutationResponse(
                status="SUCCESS",
                operation="GenerateChannelPublicationArtifact",
                product_code="",
                lifecycle_state="PUBLISHED",
                affected_sku_count=artifact.exported_sku_count,
                warnings=[],
                errors=[],
                # Pass back the secure artifact_id
                response_metadata={"artifact_id": str(artifact.artifact_id)}
            )
        except Exception as e:
            return MutationResponse(
                status="REJECTED",
                operation="GenerateChannelPublicationArtifact",
                errors=[
                    ValidationErrorDetail(
                        error_code="PUBLICATION_FAILED",
                        target_entity="CATALOG",
                        target_field="artifact",
                    )
                ]
            )

    async def get_publication_artifact_path(self, artifact_id: UUID) -> Optional[str]:
        """
        Securely retrieves the file path of a committed publication artifact.
        Enforces the Business System boundary by keeping DB schema queries internal.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT file_path FROM catalog_publication_artifacts WHERE artifact_id = $1 AND status = 'COMMITTED'",
                artifact_id
            )
            if row:
                return row["file_path"]
        return None
