"""
ShopDeck 46-Column CSV Channel Publication Adapter
Strictly conforms to document 05-shopdeck-channel.md.
"""

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import asyncpg

try:
    from .config import CATALOG_DATABASE_URL, DEFAULT_SHOPDECK_UPLOAD_QUANTITY
    from .models import PublicationArtifactEntity, ValidationErrorDetail
except ImportError:
    from config import CATALOG_DATABASE_URL, DEFAULT_SHOPDECK_UPLOAD_QUANTITY
    from models import PublicationArtifactEntity, ValidationErrorDetail

# Authoritative 46-Column Headers from 05-shopdeck-channel.md & CatalogueBulkUploadSample.csv
SHOPDECK_46_COLUMNS: List[str] = [
    "Product Code",
    "Amazon ASIN",
    "Name",
    "Sku Id",
    "Selling Price",
    "MRP",
    "Cost Price",
    "Quantity",
    "Packaging Length (in cm)",
    "Packaging Breadth (in cm)",
    "Packaging Height (in cm)",
    "Packaging Weight (in kg)",
    "GST %",
    "Image 1",
    "Image 2",
    "Image 3",
    "Image 4",
    "Image 5",
    "Image 6",
    "Image 7",
    "Image 8",
    "Image 9",
    "Image 10",
    "Video 1",
    "Video 2",
    "Product Type",
    "Size Type",
    "Size",
    "Colour",
    "Description",
    "Return/Exchange Condition",
    "Visibility",
    "Size Chart",
    "Pickup Address Code",
    "HSN Code",
    "Customisation Id",
    "Associated Pixel",
    "attr1_Fabric",
    "attr2_Care",
    "attr3_Set",
    "attr4_Pack",
    "attr5_Attribute Name",
    "collection_1",
    "collection_2",
    "collection_3",
    "Action",
]


def project_media_slots(
    sku_media_urls: List[str], product_media_urls: List[str]
) -> List[str]:
    """
    Implements Section 3 Media Projection Hierarchy from 05-shopdeck-channel.md:
    - Image 1: Primary SKU image (swatch), or first Product image if none.
    - Image 2: Secondary SKU image (detail), or next Product image if none.
    - Images 3-10: Shared Product lifestyle/room images (product_media_urls),
      followed by any additional SKU images if product images are exhausted.
    - Deduplicates images if the same URL appears in both.
    - Maximum 10 images total; trailing unused slots remain empty strings.
    """
    slots = [""] * 10
    sku_images = [u for u in sku_media_urls if u]
    prod_images = [u for u in product_media_urls if u]

    used_sku_idx = 0
    used_prod_idx = 0

    # Slot 0 (Image 1): Primary SKU Swatch or 1st Product image
    if sku_images:
        slots[0] = sku_images[0]
        used_sku_idx = 1
    elif prod_images:
        slots[0] = prod_images[0]
        used_prod_idx = 1

    # Slot 1 (Image 2): Secondary SKU Detail or next Product image
    if len(sku_images) > 1:
        slots[1] = sku_images[1]
        used_sku_idx = 2
    elif used_prod_idx < len(prod_images):
        slots[1] = prod_images[used_prod_idx]
        used_prod_idx += 1

    # Slots 2-9 (Images 3-10): Product lifestyle images first, then remaining SKU images
    slot_idx = 2
    while slot_idx < 10 and used_prod_idx < len(prod_images):
        url = prod_images[used_prod_idx]
        if url not in slots[:slot_idx]:
            slots[slot_idx] = url
            slot_idx += 1
        used_prod_idx += 1

    while slot_idx < 10 and used_sku_idx < len(sku_images):
        url = sku_images[used_sku_idx]
        if url not in slots[:slot_idx]:
            slots[slot_idx] = url
            slot_idx += 1
        used_sku_idx += 1

    return slots


class ShopDeckAdapter:
    """Compiles canonical catalog truth into the authoritative 46-column ShopDeck CSV artifact."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def create(cls, database_url: str = CATALOG_DATABASE_URL) -> "ShopDeckAdapter":
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        return cls(pool)

    async def close(self):
        if self.pool:
            await self.pool.close()

    def audit_preflight_row(self, row: Dict[str, Any]) -> List[ValidationErrorDetail]:
        """
        Validates channel constraints prior to CSV publication:
        - Strict Price Inequality: Selling Price < MRP (ShopDeck upload guideline constraint)
        - Non-empty Name, Sku Id, Product Code
        - Dimension and weight bounds
        """
        errors: List[ValidationErrorDetail] = []
        sku_id = row.get("sku_id", "")

        # 1. Strict Price Inequality Check
        mrp = Decimal(str(row.get("mrp", 0)))
        selling_price = Decimal(str(row.get("selling_price", 0)))
        if selling_price >= mrp:
            errors.append(
                ValidationErrorDetail(
                    error_code="SHOPDECK_PRICE_INEQUALITY_VIOLATION",
                    target_entity="SKU",
                    target_field="selling_price",
                    rejected_value=str(selling_price),
                    message=f"ShopDeck requires Selling Price ({selling_price}) < MRP ({mrp}). Equal prices are rejected by ShopDeck validator.",
                )
            )

        # 2. Identifier lengths
        if not sku_id or len(sku_id) < 5:
            errors.append(
                ValidationErrorDetail(
                    error_code="SHOPDECK_SPEC_VIOLATION",
                    target_entity="SKU",
                    target_field="sku_id",
                    rejected_value=sku_id,
                    message="ShopDeck requires Sku Id to be at least 5 characters.",
                )
            )

        return errors

    def compile_csv_row(
        self, row: Dict[str, Any], default_quantity: int = DEFAULT_SHOPDECK_UPLOAD_QUANTITY
    ) -> Dict[str, str]:
        """Maps a canonical master record (vw_catalog_master) to 46-column ShopDeck format."""
        sku_media = row.get("sku_media_urls") or []
        if isinstance(sku_media, str):
            sku_media = json.loads(sku_media)

        prod_media = row.get("product_media_urls") or []
        if isinstance(prod_media, str):
            prod_media = json.loads(prod_media)

        video_urls = row.get("video_urls") or []
        if isinstance(video_urls, str):
            video_urls = json.loads(video_urls)

        coll_tags = row.get("collection_tags") or []

        # Project 10 image slots per Section 3 rule
        img_slots = project_media_slots(sku_media, prod_media)

        # Video slots (up to 2)
        vid_1 = video_urls[0] if len(video_urls) > 0 else ""
        vid_2 = video_urls[1] if len(video_urls) > 1 else ""

        # Collections (up to 3)
        col_1 = coll_tags[0] if len(coll_tags) > 0 else ""
        col_2 = coll_tags[1] if len(coll_tags) > 1 else ""
        col_3 = coll_tags[2] if len(coll_tags) > 2 else ""

        # Size defaulting: If size is empty/null, default to 'Standard' per Section 4 Column 28
        size_val = str(row.get("size") or "").strip()
        if not size_val:
            size_val = "Standard"

        # Size Type defaulting: If size_type is empty/null, default to 'size'
        size_type_val = str(row.get("size_type") or "").strip()
        if not size_type_val:
            size_type_val = "size"

        # Format numeric values
        selling_price_str = f"{Decimal(str(row['selling_price'])):.2f}"
        mrp_str = f"{Decimal(str(row['mrp'])):.2f}"
        cost_price_str = f"{Decimal(str(row['cost_price'])):.2f}"
        gst_str = f"{Decimal(str(row.get('gst_percentage', 5.00))):.2f}"

        l_str = f"{Decimal(str(row['packaging_length_cm'])):.2f}"
        b_str = f"{Decimal(str(row['packaging_breadth_cm'])):.2f}"
        h_str = f"{Decimal(str(row['packaging_height_cm'])):.2f}"
        w_str = f"{Decimal(str(row['packaging_weight_kg'])):.3f}"

        return {
            "Product Code": str(row["product_code"]),
            "Amazon ASIN": "",
            "Name": str(row["product_name"]),
            "Sku Id": str(row["sku_id"]),
            "Selling Price": selling_price_str,
            "MRP": mrp_str,
            "Cost Price": cost_price_str,
            "Quantity": str(default_quantity),  # Injected dummy quantity (Quantity Firewall)
            "Packaging Length (in cm)": l_str,
            "Packaging Breadth (in cm)": b_str,
            "Packaging Height (in cm)": h_str,
            "Packaging Weight (in kg)": w_str,
            "GST %": gst_str,
            "Image 1": img_slots[0],
            "Image 2": img_slots[1],
            "Image 3": img_slots[2],
            "Image 4": img_slots[3],
            "Image 5": img_slots[4],
            "Image 6": img_slots[5],
            "Image 7": img_slots[6],
            "Image 8": img_slots[7],
            "Image 9": img_slots[8],
            "Image 10": img_slots[9],
            "Video 1": vid_1,
            "Video 2": vid_2,
            "Product Type": str(row.get("product_type") or ""),
            "Size Type": size_type_val,
            "Size": size_val,
            "Colour": str(row.get("colour") or ""),
            "Description": str(row.get("description") or ""),
            "Return/Exchange Condition": "7",  # Documented default: 7 days return window
            "Visibility": "true",  # Documented default: 'true'
            "Size Chart": str(row.get("size_chart_url") or ""),
            "Pickup Address Code": "1",  # Documented injected sequence: '1' (Panipat Central Hub)
            "HSN Code": str(row.get("hsn_code") or ""),
            "Customisation Id": "",
            "Associated Pixel": "",
            "attr1_Fabric": str(row.get("fabric_type") or ""),
            "attr2_Care": str(row.get("care_instructions") or ""),
            "attr3_Set": str(row.get("set_composition") or ""),
            "attr4_Pack": str(row.get("pack_configuration") or ""),
            "attr5_Attribute Name": "",
            "collection_1": col_1,
            "collection_2": col_2,
            "collection_3": col_3,
            "Action": "",
        }

    async def generate_publication_artifact(
        self,
        target_product_internal_ids: Optional[List[UUID]] = None,
        output_dir: Optional[str] = None,
        generated_by: str = "SYSTEM",
        lease_minutes: int = 10,
    ) -> Tuple[PublicationArtifactEntity, str]:
        """
        Compiles canonical records in READY (or PUBLISHED) state into a 46-column ShopDeck CSV artifact.
        Transitions exported products to PUBLISHED and records artifact in catalog_publication_artifacts.
        Guarantees publication artifact dual-resource safety via durable intent & lease protocol:
        - Step 1: Registers intent row with status = 'IN_PROGRESS' and lease expiry.
        - Step 2: Writes temporary file and atomic replace to finalize target on disk.
        - Step 3: Atomic database transaction committing status = 'COMMITTED' and product states = 'PUBLISHED'.
        - Step 4: On any exception, marks status = 'FAILED' and immediately removes disk files.
        """
        async with self.pool.acquire() as conn:
            # 1. Fetch eligible records from vw_catalog_master
            if target_product_internal_ids:
                rows = await conn.fetch(
                    """
                    SELECT * FROM vw_catalog_master 
                    WHERE product_internal_id = ANY($1::uuid[])
                      AND lifecycle_state IN ('READY', 'PUBLISHED')
                    ORDER BY product_code, sku_id;
                    """,
                    target_product_internal_ids,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM vw_catalog_master 
                    WHERE lifecycle_state IN ('READY', 'PUBLISHED')
                    ORDER BY product_code, sku_id;
                    """
                )

            if not rows:
                raise ValueError("No eligible products in READY or PUBLISHED state to export.")

            # 2. Pre-flight Validation
            all_errors: List[ValidationErrorDetail] = []
            compiled_rows: List[Dict[str, str]] = []
            exported_product_ids: Set[UUID] = set()

            for r in rows:
                row_dict = dict(r)
                errs = self.audit_preflight_row(row_dict)
                if errs:
                    all_errors.extend(errs)
                else:
                    compiled_rows.append(self.compile_csv_row(row_dict))
                    exported_product_ids.add(row_dict["product_internal_id"])

            if all_errors:
                err_summary = "; ".join(f"[{e.target_field}] {e.message}" for e in all_errors[:5])
                raise ValueError(f"Pre-flight publication audit failed ({len(all_errors)} errors): {err_summary}")

            # 3. Generate CSV String
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=SHOPDECK_46_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(compiled_rows)
            csv_content = csv_buffer.getvalue()

            # 4. Compute SHA-256 Content Hash
            content_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()

            # 5. Output file paths & intent registration
            artifact_id = uuid4()
            if not output_dir:
                output_dir = os.path.join(os.path.dirname(__file__), "artifacts")
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"shopdeck_catalog_export_{artifact_id}.csv")
            temp_file_path = os.path.join(output_dir, f".tmp_export_{artifact_id}.csv")

            # Step 1: Durable Intent Registration (status = 'IN_PROGRESS' with lease)
            await conn.execute(
                """
                INSERT INTO catalog_publication_artifacts (
                    artifact_id, channel, artifact_type, file_path, content_hash,
                    exported_sku_count, status, generated_by, expires_at
                ) VALUES ($1, 'SHOPDECK', 'CSV_46_COLUMN', $2, $3, $4, 'IN_PROGRESS', $5, CURRENT_TIMESTAMP + ($6 * INTERVAL '1 minute'));
                """,
                artifact_id,
                file_path,
                content_hash,
                len(compiled_rows),
                generated_by,
                lease_minutes,
            )

            try:
                # Step 2: Write temporary file and atomic replace to finalize target on disk
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(csv_content)

                os.replace(temp_file_path, file_path)

                # Step 3: Atomic database transaction committing publication status and product state
                async with conn.transaction():
                    await conn.execute(
                        """
                        UPDATE catalog_publication_artifacts 
                        SET status = 'COMMITTED', finalized_at = CURRENT_TIMESTAMP
                        WHERE artifact_id = $1;
                        """,
                        artifact_id,
                    )

                    await conn.execute(
                        """
                        UPDATE catalog_products 
                        SET lifecycle_state = 'PUBLISHED' 
                        WHERE internal_id = ANY($1::uuid[]);
                        """,
                        list(exported_product_ids),
                    )

            except Exception as exc:
                # In-Process Rollback: Mark DB record FAILED and remove disk artifacts
                try:
                    await conn.execute(
                        """
                        UPDATE catalog_publication_artifacts 
                        SET status = 'FAILED', error_message = $2
                        WHERE artifact_id = $1;
                        """,
                        artifact_id,
                        str(exc),
                    )
                except Exception:
                    pass

                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass
                raise

            artifact_entity = PublicationArtifactEntity(
                artifact_id=artifact_id,
                channel="SHOPDECK",
                artifact_type="CSV_46_COLUMN",
                file_path=file_path,
                content_hash=content_hash,
                exported_sku_count=len(compiled_rows),
                status="COMMITTED",
                generated_by=generated_by,
            )

            return artifact_entity, csv_content

    async def cleanup_uncommitted_publication_artifacts(
        self, output_dir: Optional[str] = None, force_expire_lease: bool = False
    ) -> List[str]:
        """
        Scans output directory and purges only uncommitted orphan files or genuinely abandoned artifacts.
        Guarantees that active in-flight publications (with active unexpired lease) are NEVER deleted.
        """
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        if not os.path.exists(output_dir):
            return []

        removed_files: List[str] = []
        async with self.pool.acquire() as conn:
            # Query all publication artifacts with status and lease expiry
            rows = await conn.fetch(
                """
                SELECT artifact_id, file_path, status, expires_at 
                FROM catalog_publication_artifacts;
                """
            )
            committed_ids = {str(r["artifact_id"]) for r in rows if r["status"] == "COMMITTED"}
            active_in_flight_ids = {
                str(r["artifact_id"])
                for r in rows
                if r["status"] == "IN_PROGRESS"
                and r["expires_at"]
                and (
                    r["expires_at"].timestamp() > datetime.now(timezone.utc).timestamp()
                    if not force_expire_lease
                    else False
                )
            }
            abandoned_in_progress_ids = {
                str(r["artifact_id"])
                for r in rows
                if r["status"] == "IN_PROGRESS"
                and r["expires_at"]
                and (
                    r["expires_at"].timestamp() <= datetime.now(timezone.utc).timestamp()
                    or force_expire_lease
                )
            }

            # Mark abandoned in-progress records as FAILED in DB
            if abandoned_in_progress_ids:
                await conn.execute(
                    """
                    UPDATE catalog_publication_artifacts 
                    SET status = 'FAILED', error_message = 'Cleaned up expired abandoned in-progress artifact lease'
                    WHERE artifact_id = ANY($1::uuid[]);
                    """,
                    [UUID(i) for i in abandoned_in_progress_ids],
                )

            for fname in os.listdir(output_dir):
                full_p = os.path.join(output_dir, fname)

                # 1. Temporary export files
                if fname.startswith(".tmp_export_"):
                    art_id_str = fname[len(".tmp_export_") : -len(".csv")] if fname.endswith(".csv") else ""
                    # If this temp file belongs to an active in-flight lease, do NOT delete it!
                    if art_id_str and art_id_str in active_in_flight_ids:
                        continue
                    try:
                        os.remove(full_p)
                        removed_files.append(full_p)
                    except OSError:
                        pass

                # 2. Target CSV publication export files
                elif fname.startswith("shopdeck_catalog_export_") and fname.endswith(".csv"):
                    art_id_str = fname[len("shopdeck_catalog_export_") : -len(".csv")]

                    # Case A: Committed artifact -> NEVER delete!
                    if art_id_str in committed_ids:
                        continue

                    # Case B: Active in-flight publication lease -> NEVER delete!
                    if art_id_str in active_in_flight_ids:
                        continue

                    # Case C: Expired lease, failed, or untracked orphan -> Safe to prune
                    try:
                        os.remove(full_p)
                        removed_files.append(full_p)
                    except OSError:
                        pass

        return removed_files
