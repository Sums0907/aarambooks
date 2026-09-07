"""
Unit Tests for Catalog BS Domain Models & Payloads
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from catalog.models import (
    ProductEntity,
    SKUEntity,
    PriceHistoryEntity,
    ChannelMappingEntity,
    PublicationArtifactEntity,
    IdempotencyRecordEntity,
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
    MutationResponse,
)

def test_product_entity_instantiation():
    p = ProductEntity(
        product_code="AH-MP-WATERPROOF",
        name="100% Waterproof Quilted Mattress Protector",
        description="Premium protector",
        product_type="home__bed_linen",
        brand="Aaram Homes",
        hsn_code="6304",
        gst_percentage=Decimal("5.00"),
        fabric_type="100% Cotton",
        care_instructions="Machine wash cold",
        set_composition="1 Mattress Protector",
        product_media_urls=["https://media.aaramhomes.com/img1.jpg"],
        collection_tags=["mattress-protectors"],
        lifecycle_state="DRAFT",
    )
    assert p.product_code == "AH-MP-WATERPROOF"
    assert p.brand == "Aaram Homes"
    assert p.gst_percentage == Decimal("5.00")
    assert len(p.product_media_urls) == 1

def test_sku_entity_instantiation():
    prod_id = uuid4()
    sku = SKUEntity(
        product_internal_id=prod_id,
        sku_id="126BS-BLU",
        colour="Sky Blue",
        size="King",
        size_type="size",
        pack_configuration="Pack of 1",
        mrp=Decimal("2999.00"),
        selling_price=Decimal("1499.00"),
        cost_price=Decimal("650.00"),
        packaging_length_cm=Decimal("38.00"),
        packaging_breadth_cm=Decimal("30.00"),
        packaging_height_cm=Decimal("6.00"),
        packaging_weight_kg=Decimal("1.250"),
        sku_media_urls=["https://media.aaramhomes.com/blue_swatch.jpg"],
    )
    assert sku.sku_id == "126BS-BLU"
    assert sku.product_internal_id == prod_id
    assert sku.mrp > sku.selling_price

def test_save_product_family_payload():
    payload = SaveProductFamilyPayload(
        idempotency_key="test-key-123",
        product=SaveProductInput(
            product_code="AH-BS-PASTEL",
            name="Pastel Bedsheet Collection",
        ),
        skus=[
            SaveSkuInput(
                sku_id="101CC-SUN",
                colour="Sunflower Yellow",
                size="Queen",
                mrp=Decimal("1999.00"),
                selling_price=Decimal("999.00"),
                cost_price=Decimal("450.00"),
                packaging_length_cm=Decimal("30.00"),
                packaging_breadth_cm=Decimal("25.00"),
                packaging_height_cm=Decimal("5.00"),
                packaging_weight_kg=Decimal("0.800"),
            )
        ],
    )
    assert payload.product.product_code == "AH-BS-PASTEL"
    assert len(payload.skus) == 1
    assert payload.skus[0].sku_id == "101CC-SUN"
