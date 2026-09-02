"""
Catalog BS → AZM Persistent Database Configuration & Ingestion

Reads the Catalog Public Contracts and maps them into the declarative
AzmIngestionConfig for the UniversalAzmIngester.

ARCHITECTURAL INVARIANTS:
  - The mechanics of database writes, idempotency, and transaction management
    are deferred to the UniversalAzmIngester.
  - This file purely declares the specific knowledge structure of the Catalog BS.
"""
import pathlib
from typing import Optional

from src.azm.config import (
    AZM_CATALOG_SEMANTIC_CONTRACT_PATH,
    AZM_CATALOG_SCHEMATIC_CONTRACT_PATH,
    CATALOG_NAMESPACE_NAME,
    CATALOG_NAMESPACE_CLASSIFICATION,
    CATALOG_CONTRACT_VERSION,
)
from src.azm.ingestion.universal_ingester import (
    UniversalAzmIngester,
    AzmIngestionConfig,
    AzmConceptDef,
    AzmRelationshipDef,
    AzmSchematicViewDef,
    AzmSchematicFieldDef,
    AzmExternalMappingDef,
)

# ---------------------------------------------------------------------------
# Contract reading
# ---------------------------------------------------------------------------

def _read_contract(relative_path: str) -> str:
    p = pathlib.Path(relative_path)
    if p.is_absolute():
        if not p.exists():
            raise FileNotFoundError(f"Contract not found: {p}")
        return p.read_text(encoding="utf-8")
    
    project_root = pathlib.Path(__file__).parents[3]
    full_path = project_root / relative_path
    if not full_path.exists():
        raise FileNotFoundError(f"Contract not found: {full_path}")
    return full_path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Catalog Configuration Definitions
# ---------------------------------------------------------------------------

_EXPLICIT_ATTR_CONCEPT_MAP = {
    ("vw_catalog_products", "product_name"):         "catalog.entity.product",
    ("vw_catalog_products", "description"):          "catalog.entity.product",
    ("vw_catalog_skus", "product_name"):             "catalog.entity.product",
    ("vw_catalog_skus", "colour"):                   "catalog.entity.sku",
    ("vw_catalog_skus", "size"):                     "catalog.entity.sku",
    ("vw_catalog_skus", "mrp"):                      "catalog.entity.sku",
    ("vw_catalog_skus", "selling_price"):            "catalog.entity.sku",
    ("vw_catalog_skus", "cost_price"):               "catalog.entity.sku",
    ("vw_catalog_skus", "gross_margin"):             "catalog.entity.sku",
    ("vw_catalog_skus", "packaging_length_cm"):      "catalog.entity.sku",
    ("vw_catalog_skus", "packaging_breadth_cm"):     "catalog.entity.sku",
    ("vw_catalog_skus", "packaging_height_cm"):      "catalog.entity.sku",
    ("vw_catalog_skus", "packaging_weight_kg"):      "catalog.entity.sku",
    ("vw_catalog_master", "product_name"):           "catalog.entity.product",
    ("vw_catalog_master", "colour"):                 "catalog.entity.sku",
    ("vw_catalog_master", "size"):                   "catalog.entity.sku",
    ("vw_catalog_master", "mrp"):                    "catalog.entity.sku",
    ("vw_catalog_master", "selling_price"):          "catalog.entity.sku",
    ("vw_catalog_master", "cost_price"):             "catalog.entity.sku",
    ("vw_catalog_master", "gross_margin"):           "catalog.entity.sku",
    ("vw_catalog_master", "packaging_length_cm"):    "catalog.entity.sku",
    ("vw_catalog_master", "packaging_breadth_cm"):   "catalog.entity.sku",
    ("vw_catalog_master", "packaging_height_cm"):    "catalog.entity.sku",
    ("vw_catalog_master", "packaging_weight_kg"):    "catalog.entity.sku",
}

_DERIVED_FIELDS = {
    ("vw_catalog_skus", "gross_margin"),
    ("vw_catalog_master", "gross_margin"),
}

_CHANNEL_FIELDS = {
    ("vw_catalog_master", "shopdeck_sku_id"),
    ("vw_catalog_master", "shopdeck_product_id"),
}

_VIEW_FIELDS = {
    "vw_catalog_products": [
        ("product_internal_id",  "TEXT",      "Technical primary key (AZM does NOT use this as its UUID)"),
        ("product_code",         "TEXT",      "Commercial grouping code for sibling SKUs"),
        ("product_name",         "TEXT",      "Commercial title of the product"),
        ("description",          "TEXT",      "Storytelling narrative description"),
        ("product_type",         "TEXT",      "Type classification of the product"),
        ("brand",                "TEXT",      "Brand name"),
        ("hsn_code",             "TEXT",      "Harmonised System Nomenclature code for GST"),
        ("gst_percentage",       "NUMERIC",   "GST rate applicable to this product"),
        ("fabric_type",          "TEXT",      "Material / fabric composition"),
        ("care_instructions",    "TEXT",      "Washing and care guidelines"),
        ("set_composition",      "TEXT",      "Set/bundle composition description"),
        ("product_media_urls",   "TEXT",      "Lifestyle media URLs (JSON array)"),
        ("size_chart_url",       "TEXT",      "Size chart image URL"),
        ("video_urls",           "TEXT",      "Product video URLs (JSON array)"),
        ("collection_tags",      "TEXT",      "Collection/category tags (JSON array)"),
        ("lifecycle_state",      "TEXT",      "Catalog BS lifecycle status (DRAFT/ACTIVE/ARCHIVED)"),
        ("created_at",           "TIMESTAMP", "Record creation timestamp"),
        ("updated_at",           "TIMESTAMP", "Record last-updated timestamp"),
    ],
    "vw_catalog_skus": [
        ("sku_internal_id",        "TEXT",      "Technical SKU primary key"),
        ("product_internal_id",    "TEXT",      "Technical product primary key (FK)"),
        ("product_code",           "TEXT",      "Parent product code"),
        ("product_name",           "TEXT",      "Parent product commercial title"),
        ("sku_id",                 "TEXT",      "Sovereign operational key (e.g. 126BS-RED)"),
        ("colour",                 "TEXT",      "Physical colour variation"),
        ("size",                   "TEXT",      "Physical size variation"),
        ("size_type",              "TEXT",      "Size type classification (e.g. numeric, alpha)"),
        ("pack_configuration",     "TEXT",      "Packing configuration (e.g. single, set)"),
        ("mrp",                    "NUMERIC",   "Maximum Retail Price"),
        ("selling_price",          "NUMERIC",   "Storefront base selling price"),
        ("cost_price",             "NUMERIC",   "Manufactured cost price"),
        ("gross_margin",           "NUMERIC",   "Derived: selling_price - cost_price"),
        ("packaging_length_cm",    "NUMERIC",   "Packaging length in centimetres"),
        ("packaging_breadth_cm",   "NUMERIC",   "Packaging breadth in centimetres"),
        ("packaging_height_cm",    "NUMERIC",   "Packaging height in centimetres"),
        ("packaging_weight_kg",    "NUMERIC",   "Packaging weight in kilograms"),
        ("sku_media_urls",         "TEXT",      "SKU physical swatch media URLs (JSON array)"),
        ("created_at",             "TIMESTAMP", "Record creation timestamp"),
        ("updated_at",             "TIMESTAMP", "Record last-updated timestamp"),
    ],
    "vw_catalog_master": [
        ("sku_internal_id",        "TEXT",      "Technical SKU primary key"),
        ("product_internal_id",    "TEXT",      "Technical product primary key"),
        ("sku_id",                 "TEXT",      "Sovereign operational SKU key"),
        ("product_code",           "TEXT",      "Parent product code"),
        ("product_name",           "TEXT",      "Parent product name"),
        ("description",            "TEXT",      "Product description"),
        ("product_type",           "TEXT",      "Product type classification"),
        ("brand",                  "TEXT",      "Brand name"),
        ("hsn_code",               "TEXT",      "HSN code"),
        ("gst_percentage",         "NUMERIC",   "GST rate"),
        ("fabric_type",            "TEXT",      "Fabric composition"),
        ("care_instructions",      "TEXT",      "Care guidelines"),
        ("set_composition",        "TEXT",      "Set composition"),
        ("colour",                 "TEXT",      "Colour variation"),
        ("size",                   "TEXT",      "Size variation"),
        ("size_type",              "TEXT",      "Size type"),
        ("pack_configuration",     "TEXT",      "Pack configuration"),
        ("mrp",                    "NUMERIC",   "Maximum Retail Price"),
        ("selling_price",          "NUMERIC",   "Storefront base selling price"),
        ("cost_price",             "NUMERIC",   "Manufactured cost price"),
        ("gross_margin",           "NUMERIC",   "Derived: selling_price - cost_price"),
        ("packaging_length_cm",    "NUMERIC",   "Packaging length cm"),
        ("packaging_breadth_cm",   "NUMERIC",   "Packaging breadth cm"),
        ("packaging_height_cm",    "NUMERIC",   "Packaging height cm"),
        ("packaging_weight_kg",    "NUMERIC",   "Packaging weight kg"),
        ("sku_media_urls",         "TEXT",      "SKU media URLs"),
        ("product_media_urls",     "TEXT",      "Product media URLs"),
        ("size_chart_url",         "TEXT",      "Size chart URL"),
        ("video_urls",             "TEXT",      "Video URLs"),
        ("collection_tags",        "TEXT",      "Collection tags"),
        ("lifecycle_state",        "TEXT",      "Product lifecycle state"),
        ("shopdeck_sku_id",        "TEXT",      "ShopDeck channel SKU token (EXTERNAL_CHANNEL)"),
        ("shopdeck_product_id",    "TEXT",      "ShopDeck channel product token (EXTERNAL_CHANNEL)"),
        ("created_at",             "TIMESTAMP", "Creation timestamp"),
        ("updated_at",             "TIMESTAMP", "Last-updated timestamp"),
    ],
}

_VIEW_DESCRIPTIONS = {
    "vw_catalog_products": "Product-level commercial data. One row per Product (commercial family).",
    "vw_catalog_skus":     "SKU-level sellable unit data. One row per physical sellable variant.",
    "vw_catalog_master":   "Unified read projection combining Product + SKU + channel mapping tokens.",
}

# ---------------------------------------------------------------------------
# Main ingestion entry point
# ---------------------------------------------------------------------------

def ingest_catalog(db_url: Optional[str] = None) -> dict:
    """
    Builds the declarative ingestion configuration for Catalog and executes it
    via the UniversalAzmIngester.
    """
    semantic_content = _read_contract(AZM_CATALOG_SEMANTIC_CONTRACT_PATH)
    schematic_content = _read_contract(AZM_CATALOG_SCHEMATIC_CONTRACT_PATH)

    # Define Concepts
    product_concept = AzmConceptDef(
        semantic_key="catalog.entity.product",
        concept_name="Product",
        concept_type="ENTITY",
        definition="A commercial grouping or design family under which one or more sellable SKUs are presented to customers as a single offering.",
        source_element="Section 2.1 — Product (Commercial Family / Parent)",
        aliases=["product", "product family", "commercial family", "parent"],
    )
    sku_concept = AzmConceptDef(
        semantic_key="catalog.entity.sku",
        concept_name="SKU",
        concept_type="ENTITY",
        definition="The discrete, sellable, physical unit that is priced, packed, and shipped. The atomic operational unit of commerce.",
        source_element="Section 2.2 — SKU (Sellable Commercial Unit / Child)",
        aliases=["sku", "sellable unit", "variant", "child", "product variant"],
    )

    # Define Relationships
    containment_rel = AzmRelationshipDef(
        source_key="catalog.entity.product",
        target_key="catalog.entity.sku",
        relationship_type="CONTAINS",
        derivation_rule="catalog_2tier_containment",
        source_element="Section 2 — 2-Tier Model (Product=Parent, SKU=Child)",
    )

    # Define Views & Fields
    views = []
    for view_name, fields in _VIEW_FIELDS.items():
        field_defs = []
        for (field_name, field_type, description) in fields:
            mapped_key = _EXPLICIT_ATTR_CONCEPT_MAP.get((view_name, field_name))
            field_defs.append(AzmSchematicFieldDef(
                field_name=field_name,
                field_type=field_type,
                description=description,
                is_derived=((view_name, field_name) in _DERIVED_FIELDS),
                is_channel_field=((view_name, field_name) in _CHANNEL_FIELDS),
                mapped_concept_key=mapped_key,
            ))
        views.append(AzmSchematicViewDef(
            view_name=view_name,
            description=_VIEW_DESCRIPTIONS.get(view_name, ""),
            surface_type="SQL_VIEW",
            fields=field_defs,
        ))

    # Define External Mappings
    external_mappings = [
        AzmExternalMappingDef(
            native_concept_key="catalog.entity.sku",
            external_system="shopdeck",
            external_key="customer_sku_short_id",
            display_name="ShopDeck customer_sku_short_id",
        ),
        AzmExternalMappingDef(
            native_concept_key="catalog.entity.product",
            external_system="shopdeck",
            external_key="customer_product_short_id",
            display_name="ShopDeck customer_product_short_id",
        ),
    ]

    config = AzmIngestionConfig(
        source_bs="catalog",
        namespace_name=CATALOG_NAMESPACE_NAME,
        namespace_classification=CATALOG_NAMESPACE_CLASSIFICATION,
        namespace_description="Aaram Catalog Business System — commercial product and SKU knowledge",
        contract_version=CATALOG_CONTRACT_VERSION,
        semantic_contract_content=semantic_content,
        schematic_contract_content=schematic_content,
        semantic_source_element="catalog-semantic-public-contract.md",
        schematic_source_element="public_views.sql — Catalog Schematic Public Contract v1.1",
        concepts=[product_concept, sku_concept],
        relationships=[containment_rel],
        views=views,
        external_mappings=external_mappings,
    )

    ingester = UniversalAzmIngester(db_url)
    return ingester.ingest(config)


