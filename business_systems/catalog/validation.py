"""
Deterministic Validation Engine for Catalog BS
Strictly enforces business rules from 03-catalog-business-rules.md.
"""

import re
from decimal import Decimal
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse

try:
    from .models import (
        ProductEntity,
        SKUEntity,
        SaveProductFamilyPayload,
        SaveProductInput,
        SaveSkuInput,
        ValidationErrorDetail,
        ValidationReport,
    )
except ImportError:
    from models import (
        ProductEntity,
        SKUEntity,
        SaveProductFamilyPayload,
        SaveProductInput,
        SaveSkuInput,
        ValidationErrorDetail,
        ValidationReport,
    )

# Regex matching uppercase alphanumeric characters separated by single hyphens
IDENTIFIER_REGEX = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)*$")
HSN_REGEX = re.compile(r"^[0-9]+$")
ALLOWED_GST_RATES: Set[Decimal] = {
    Decimal("0.00"),
    Decimal("5.00"),
    Decimal("12.00"),
    Decimal("18.00"),
    Decimal("28.00"),
}


def validate_sku_id(sku_id: str) -> Optional[ValidationErrorDetail]:
    """
    Validates Rule SKU-01:
    - 5 <= length <= 10
    - Uppercase alphanumeric and hyphens
    - Regex: ^[A-Z0-9]+(-[A-Z0-9]+)*$
    """
    if not sku_id or not isinstance(sku_id, str):
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity="SKU",
            target_field="sku_id",
            rejected_value=sku_id,
            message="SKU ID is mandatory and must be a non-empty string.",
        )

    if len(sku_id) < 5 or len(sku_id) > 10:
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity="SKU",
            target_field="sku_id",
            rejected_value=sku_id,
            message=f"SKU ID '{sku_id}' length ({len(sku_id)}) must be between 5 and 10 characters.",
        )

    if not IDENTIFIER_REGEX.match(sku_id):
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity="SKU",
            target_field="sku_id",
            rejected_value=sku_id,
            message=f"SKU ID '{sku_id}' must be uppercase alphanumeric with optional single hyphens.",
        )

    return None


def validate_product_code(product_code: str) -> Optional[ValidationErrorDetail]:
    """
    Validates Rule PRD-01 and PRD-02:
    - 5 <= length < 25 (i.e. length <= 24)
    - Uppercase alphanumeric and hyphens
    - Regex: ^[A-Z0-9]+(-[A-Z0-9]+)*$
    """
    if not product_code or not isinstance(product_code, str):
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity="PRODUCT",
            target_field="product_code",
            rejected_value=product_code,
            message="Product Code is mandatory and must be a non-empty string.",
        )

    if len(product_code) < 5 or len(product_code) >= 25:
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity="PRODUCT",
            target_field="product_code",
            rejected_value=product_code,
            message=f"Product Code '{product_code}' length ({len(product_code)}) must be between 5 and 24 characters.",
        )

    if not IDENTIFIER_REGEX.match(product_code):
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity="PRODUCT",
            target_field="product_code",
            rejected_value=product_code,
            message=f"Product Code '{product_code}' must be uppercase alphanumeric with optional single hyphens.",
        )

    return None


def validate_pricing(
    mrp: Decimal, selling_price: Decimal, cost_price: Decimal
) -> Tuple[List[ValidationErrorDetail], List[str]]:
    """
    Validates Rule PRC-01, PRC-02, PRC-03:
    - mrp > 0, selling_price > 0, cost_price > 0
    - selling_price <= mrp (Hard Error)
    - cost_price > selling_price (Warning)
    """
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

    if mrp is None or mrp <= Decimal("0"):
        errors.append(
            ValidationErrorDetail(
                error_code="PRICING_INVARIANT_VIOLATION",
                target_entity="SKU",
                target_field="mrp",
                rejected_value=str(mrp),
                message="MRP must be greater than zero.",
            )
        )

    if selling_price is None or selling_price <= Decimal("0"):
        errors.append(
            ValidationErrorDetail(
                error_code="PRICING_INVARIANT_VIOLATION",
                target_entity="SKU",
                target_field="selling_price",
                rejected_value=str(selling_price),
                message="Selling Price must be greater than zero.",
            )
        )

    if cost_price is None or cost_price <= Decimal("0"):
        errors.append(
            ValidationErrorDetail(
                error_code="PRICING_INVARIANT_VIOLATION",
                target_entity="SKU",
                target_field="cost_price",
                rejected_value=str(cost_price),
                message="Cost Price must be greater than zero.",
            )
        )

    if mrp is not None and selling_price is not None:
        if mrp > Decimal("0") and selling_price > Decimal("0") and selling_price > mrp:
            errors.append(
                ValidationErrorDetail(
                    error_code="PRICING_INVARIANT_VIOLATION",
                    target_entity="SKU",
                    target_field="selling_price",
                    rejected_value=str(selling_price),
                    message=f"Selling Price ({selling_price}) cannot exceed MRP ({mrp}).",
                )
            )

    if (
        cost_price is not None
        and selling_price is not None
        and cost_price > selling_price
    ):
        warnings.append(
            f"Loss-leader warning: Cost Price ({cost_price}) exceeds Selling Price ({selling_price})."
        )

    return errors, warnings


def validate_dimensions(
    length_cm: Decimal, breadth_cm: Decimal, height_cm: Decimal, weight_kg: Decimal
) -> List[ValidationErrorDetail]:
    """
    Validates Rule DIM-01 & DIM-02:
    - 1.00 <= L, B, H <= 50.00 cm
    - 0.050 <= W <= 10.000 kg
    """
    errors: List[ValidationErrorDetail] = []

    for name, val in [
        ("packaging_length_cm", length_cm),
        ("packaging_breadth_cm", breadth_cm),
        ("packaging_height_cm", height_cm),
    ]:
        if val is None or val < Decimal("1.00") or val > Decimal("50.00"):
            errors.append(
                ValidationErrorDetail(
                    error_code="PHYSICAL_SPEC_VIOLATION",
                    target_entity="SKU",
                    target_field=name,
                    rejected_value=str(val),
                    message=f"{name} ({val}) must be between 1.00 cm and 50.00 cm.",
                )
            )

    if weight_kg is None or weight_kg < Decimal("0.050") or weight_kg > Decimal("10.000"):
        errors.append(
            ValidationErrorDetail(
                error_code="PHYSICAL_SPEC_VIOLATION",
                target_entity="SKU",
                target_field="packaging_weight_kg",
                rejected_value=str(weight_kg),
                message=f"packaging_weight_kg ({weight_kg}) must be between 0.050 kg and 10.000 kg.",
            )
        )

    return errors


def validate_tax_attributes(
    hsn_code: Optional[str], gst_percentage: Decimal
) -> List[ValidationErrorDetail]:
    """
    Validates Rule TAX-01 & TAX-02:
    - gst_percentage in {0.00, 5.00, 12.00, 18.00, 28.00}
    - hsn_code: >= 4 digits, numeric
    """
    errors: List[ValidationErrorDetail] = []

    if gst_percentage not in ALLOWED_GST_RATES:
        errors.append(
            ValidationErrorDetail(
                error_code="TAX_SPEC_VIOLATION",
                target_entity="PRODUCT",
                target_field="gst_percentage",
                rejected_value=str(gst_percentage),
                message=f"GST percentage ({gst_percentage}) must be one of {sorted([float(r) for r in ALLOWED_GST_RATES])}.",
            )
        )

    if hsn_code is not None:
        if len(hsn_code) < 4 or not HSN_REGEX.match(hsn_code):
            errors.append(
                ValidationErrorDetail(
                    error_code="TAX_SPEC_VIOLATION",
                    target_entity="PRODUCT",
                    target_field="hsn_code",
                    rejected_value=hsn_code,
                    message=f"HSN code '{hsn_code}' must contain at least 4 numeric digits without spaces.",
                )
            )

    return errors


def validate_url(url: str, field_name: str, entity: str) -> Optional[ValidationErrorDetail]:
    """Validates HTTP/HTTPS URL format."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ValidationErrorDetail(
                error_code="SYNTAX_VALIDATION_ERROR",
                target_entity=entity,
                target_field=field_name,
                rejected_value=url,
                message=f"Invalid URL '{url}' for {field_name}. Must be a valid http or https URL.",
            )
    except Exception:
        return ValidationErrorDetail(
            error_code="SYNTAX_VALIDATION_ERROR",
            target_entity=entity,
            target_field=field_name,
            rejected_value=url,
            message=f"Malformed URL '{url}' for {field_name}.",
        )
    return None


def validate_sku_input(sku: SaveSkuInput) -> ValidationReport:
    """Validates a single SaveSkuInput payload."""
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

    # 1. SKU ID
    err = validate_sku_id(sku.sku_id)
    if err:
        errors.append(err)

    # 2. Pricing
    p_errs, p_warns = validate_pricing(sku.mrp, sku.selling_price, sku.cost_price)
    errors.extend(p_errs)
    warnings.extend(p_warns)

    # 3. Dimensions
    errors.extend(
        validate_dimensions(
            sku.packaging_length_cm,
            sku.packaging_breadth_cm,
            sku.packaging_height_cm,
            sku.packaging_weight_kg,
        )
    )

    # 4. Media URLs
    for url in sku.sku_media_urls:
        u_err = validate_url(url, "sku_media_urls", "SKU")
        if u_err:
            errors.append(u_err)

    # 5. Size type
    if sku.size_type is not None and sku.size_type not in ("size", "variant"):
        errors.append(
            ValidationErrorDetail(
                error_code="SYNTAX_VALIDATION_ERROR",
                target_entity="SKU",
                target_field="size_type",
                rejected_value=sku.size_type,
                message="size_type must be either 'size' or 'variant'.",
            )
        )

    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_product_input(product: SaveProductInput) -> ValidationReport:
    """Validates a single SaveProductInput payload."""
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

    # 1. Product Code
    err = validate_product_code(product.product_code)
    if err:
        errors.append(err)

    # 2. Product Name
    if not product.name or len(product.name.strip()) < 5:
        errors.append(
            ValidationErrorDetail(
                error_code="SYNTAX_VALIDATION_ERROR",
                target_entity="PRODUCT",
                target_field="name",
                rejected_value=product.name,
                message="Product name must be at least 5 characters.",
            )
        )

    # 3. Tax attributes
    errors.extend(validate_tax_attributes(product.hsn_code, product.gst_percentage))

    # 4. Media URLs
    for url in product.product_media_urls:
        u_err = validate_url(url, "product_media_urls", "PRODUCT")
        if u_err:
            errors.append(u_err)

    if product.size_chart_url:
        u_err = validate_url(product.size_chart_url, "size_chart_url", "PRODUCT")
        if u_err:
            errors.append(u_err)

    for url in product.video_urls:
        u_err = validate_url(url, "video_urls", "PRODUCT")
        if u_err:
            errors.append(u_err)

    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_product_family_payload(payload: SaveProductFamilyPayload) -> ValidationReport:
    """Validates entire inbound SaveProductFamily payload."""
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

    # Validate Product
    p_report = validate_product_input(payload.product)
    errors.extend(p_report.errors)
    warnings.extend(p_report.warnings)

    # Sibling SKU uniqueness check in payload
    seen_skus: Set[str] = set()
    for sku in payload.skus:
        if sku.sku_id in seen_skus:
            errors.append(
                ValidationErrorDetail(
                    error_code="SKU_COLLISION",
                    target_entity="SKU",
                    target_field="sku_id",
                    rejected_value=sku.sku_id,
                    message=f"Duplicate SKU ID '{sku.sku_id}' provided in the same mutation payload.",
                )
            )
        seen_skus.add(sku.sku_id)

        sku_report = validate_sku_input(sku)
        errors.extend(sku_report.errors)
        warnings.extend(sku_report.warnings)

    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_readiness_gate(
    product: SaveProductInput, skus: List[SaveSkuInput]
) -> ValidationReport:
    """
    Validates completeness invariants for transition from DRAFT to READY (Rule LIF-01 & Table 5):
    - Product: name (>= 5 chars), description, product_type, gst_percentage
    - SKUs: >= 1 child SKU
    - Each SKU: mrp, selling_price, cost_price, packaging dimensions, weight, and >= 1 sku_media_urls (Rule MED-02).
    """
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

    # Must pass standard syntax validations
    base_report = validate_product_family_payload(
        SaveProductFamilyPayload(product=product, skus=skus)
    )
    errors.extend(base_report.errors)
    warnings.extend(base_report.warnings)

    # Must have at least 1 child SKU
    if not skus:
        errors.append(
            ValidationErrorDetail(
                error_code="LIFECYCLE_COMPLETENESS_ERROR",
                target_entity="PRODUCT",
                target_field="skus",
                message="Cannot transition Product to READY without at least one child SKU.",
            )
        )

    # Product name mandatory (min 5 chars for publication)
    if not product.name or len(product.name.strip()) < 5:
        errors.append(
            ValidationErrorDetail(
                error_code="LIFECYCLE_COMPLETENESS_ERROR",
                target_entity="PRODUCT",
                target_field="name",
                rejected_value=product.name,
                message="Product Name must be at least 5 characters for publication readiness.",
            )
        )

    # Product description mandatory for READY
    if not product.description or not product.description.strip():
        errors.append(
            ValidationErrorDetail(
                error_code="LIFECYCLE_COMPLETENESS_ERROR",
                target_entity="PRODUCT",
                target_field="description",
                message="Product description is required for READY state.",
            )
        )

    # Product type taxonomy mandatory for READY
    if not product.product_type or not product.product_type.strip():
        errors.append(
            ValidationErrorDetail(
                error_code="LIFECYCLE_COMPLETENESS_ERROR",
                target_entity="PRODUCT",
                target_field="product_type",
                message="Product type taxonomy is required for READY state.",
            )
        )

    # SKU level completeness
    for sku in skus:
        # Rule MED-02: Every SKU must have at least 1 primary image
        valid_sku_media = [u for u in sku.sku_media_urls if u and str(u).strip()]
        if not valid_sku_media:
            errors.append(
                ValidationErrorDetail(
                    error_code="LIFECYCLE_COMPLETENESS_ERROR",
                    target_entity="SKU",
                    target_field="sku_media_urls",
                    rejected_value="[]",
                    message=f"SKU '{sku.sku_id}' must have at least one primary media URL (Rule MED-02) for READY state.",
                )
            )

        if sku.mrp is None or sku.mrp <= 0:
            errors.append(
                ValidationErrorDetail(
                    error_code="LIFECYCLE_COMPLETENESS_ERROR",
                    target_entity="SKU",
                    target_field="mrp",
                    rejected_value=str(sku.mrp),
                    message=f"SKU '{sku.sku_id}' MRP is required and must be > 0 for READY state.",
                )
            )

        if sku.selling_price is None or sku.selling_price <= 0:
            errors.append(
                ValidationErrorDetail(
                    error_code="LIFECYCLE_COMPLETENESS_ERROR",
                    target_entity="SKU",
                    target_field="selling_price",
                    rejected_value=str(sku.selling_price),
                    message=f"SKU '{sku.sku_id}' Selling Price is required and must be > 0 for READY state.",
                )
            )

        if sku.cost_price is None or sku.cost_price <= 0:
            errors.append(
                ValidationErrorDetail(
                    error_code="LIFECYCLE_COMPLETENESS_ERROR",
                    target_entity="SKU",
                    target_field="cost_price",
                    rejected_value=str(sku.cost_price),
                    message=f"SKU '{sku.sku_id}' Cost Price is required and must be > 0 for READY state.",
                )
            )

    return ValidationReport(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
