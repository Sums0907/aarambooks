"""
Unit Tests for Catalog BS Deterministic Validation Engine
Strictly validates all rules from 03-catalog-business-rules.md.
"""

import pytest
from decimal import Decimal
from catalog.models import SaveProductFamilyPayload, SaveProductInput, SaveSkuInput
from catalog.validation import (
    validate_sku_id,
    validate_product_code,
    validate_pricing,
    validate_dimensions,
    validate_tax_attributes,
    validate_product_family_payload,
    validate_readiness_gate,
)


def test_sku_id_validation():
    # Valid SKUs
    assert validate_sku_id("126BS") is None
    assert validate_sku_id("126BS-BLU") is None
    assert validate_sku_id("101CC-SUN") is None
    assert validate_sku_id("103OTTO") is None
    assert validate_sku_id("A1B2C-D3E4") is None

    # Invalid length (< 5)
    err = validate_sku_id("12BS")
    assert err is not None
    assert err.error_code == "SYNTAX_VALIDATION_ERROR"

    # Invalid length (> 10)
    err = validate_sku_id("12345678901")
    assert err is not None

    # Invalid lowercase
    err = validate_sku_id("126bs-blu")
    assert err is not None

    # Invalid leading/trailing/consecutive hyphens
    assert validate_sku_id("-126BS") is not None
    assert validate_sku_id("126BS-") is not None
    assert validate_sku_id("126--BS") is not None
    assert validate_sku_id("126_BS") is not None  # Underscore prohibited


def test_product_code_validation():
    # Valid Product Codes
    assert validate_product_code("AH-MP-WATERPROOF") is None
    assert validate_product_code("AH-BS-PASTELGARDEN") is None
    assert validate_product_code("AH-1234") is None

    # Invalid length (< 5)
    assert validate_product_code("AH-1") is not None

    # Invalid length (>= 25)
    assert validate_product_code("AH-MP-WATERPROOF-PREMIUM-EXT") is not None

    # Invalid lowercase
    assert validate_product_code("ah-mp-waterproof") is not None

    # Invalid consecutive hyphens
    assert validate_product_code("AH--MP") is not None


def test_pricing_validation():
    # Valid pricing
    errors, warnings = validate_pricing(Decimal("2999.00"), Decimal("1499.00"), Decimal("650.00"))
    assert len(errors) == 0
    assert len(warnings) == 0

    # Price ceiling violation: selling_price > mrp
    errors, warnings = validate_pricing(Decimal("1000.00"), Decimal("1500.00"), Decimal("500.00"))
    assert len(errors) == 1
    assert errors[0].error_code == "PRICING_INVARIANT_VIOLATION"

    # Loss-leader detection: cost_price > selling_price
    errors, warnings = validate_pricing(Decimal("2000.00"), Decimal("800.00"), Decimal("950.00"))
    assert len(errors) == 0
    assert len(warnings) == 1
    assert "Loss-leader warning" in warnings[0]

    # Non-positive prices
    errors, _ = validate_pricing(Decimal("0.00"), Decimal("100.00"), Decimal("50.00"))
    assert len(errors) == 1


def test_dimensions_validation():
    # Valid dimensions
    errors = validate_dimensions(Decimal("38.00"), Decimal("30.00"), Decimal("6.00"), Decimal("1.250"))
    assert len(errors) == 0

    # Exceeding length (> 50 cm)
    errors = validate_dimensions(Decimal("55.00"), Decimal("30.00"), Decimal("6.00"), Decimal("1.250"))
    assert len(errors) == 1
    assert errors[0].target_field == "packaging_length_cm"

    # Weight underflow (< 0.050 kg)
    errors = validate_dimensions(Decimal("30.00"), Decimal("20.00"), Decimal("5.00"), Decimal("0.010"))
    assert len(errors) == 1
    assert errors[0].target_field == "packaging_weight_kg"


def test_tax_attributes_validation():
    # Valid GST rates
    assert len(validate_tax_attributes("6304", Decimal("5.00"))) == 0
    assert len(validate_tax_attributes("6302", Decimal("12.00"))) == 0

    # Invalid GST rate
    errs = validate_tax_attributes("6304", Decimal("7.00"))
    assert len(errs) == 1
    assert errs[0].error_code == "TAX_SPEC_VIOLATION"

    # Invalid HSN code (short or non-numeric)
    errs = validate_tax_attributes("63", Decimal("5.00"))
    assert len(errs) == 1
    assert errs[0].target_field == "hsn_code"

    errs = validate_tax_attributes("63A4", Decimal("5.00"))
    assert len(errs) == 1


def test_sibling_sku_collision_in_payload():
    payload = SaveProductFamilyPayload(
        product=SaveProductInput(product_code="AH-TEST-FAM", name="Test Family"),
        skus=[
            SaveSkuInput(
                sku_id="126BS-BLU",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("30.00"),
                packaging_breadth_cm=Decimal("20.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("1.000"),
            ),
            SaveSkuInput(
                sku_id="126BS-BLU",  # Collision!
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("30.00"),
                packaging_breadth_cm=Decimal("20.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("1.000"),
            ),
        ],
    )
    report = validate_product_family_payload(payload)
    assert not report.is_valid
    assert any(e.error_code == "SKU_COLLISION" for e in report.errors)


def test_readiness_gate_validation():
    # Incomplete product (no SKUs)
    report = validate_readiness_gate(
        product=SaveProductInput(product_code="AH-READY-01", name="Ready Product"),
        skus=[],
    )
    assert not report.is_valid
    assert any(e.error_code == "LIFECYCLE_COMPLETENESS_ERROR" for e in report.errors)

    # Complete product
    report = validate_readiness_gate(
        product=SaveProductInput(
            product_code="AH-READY-01",
            name="Ready Product Title",
            description="<p>Full commercial description</p>",
            product_type="home__bed_linen",
            brand="Aaram Homes",
            gst_percentage=Decimal("5.00"),
        ),
        skus=[
            SaveSkuInput(
                sku_id="READY-SKU1",
                mrp=Decimal("2000.00"),
                selling_price=Decimal("1000.00"),
                cost_price=Decimal("500.00"),
                packaging_length_cm=Decimal("30.00"),
                packaging_breadth_cm=Decimal("20.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("1.000"),
                sku_media_urls=["https://media.aaramhomes.com/ready_swatch.jpg"],
            )
        ],
    )
    assert report.is_valid
