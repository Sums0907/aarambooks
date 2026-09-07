import pytest
from src.azm.db import get_connection
from src.azm.ingestion.contract_parser import ingest_contracts

def setup_module(module):
    # Ensure contracts are ingested into the test DB
    from src.azm.db import execute_schema
    conn = get_connection()
    execute_schema(conn)
    
    # Ingest catalog
    ingest_contracts(
        "business_systems/catalog/public-contracts/catalog-semantic-public-contract.md",
        "business_systems/catalog/public-contracts/catalog-schematic-public-contract.md"
    )
    # Ingest shopdeck
    ingest_contracts(
        "business_systems/shopdeck/public-contracts/shopdeck-semantic-public-contract.md",
        "business_systems/shopdeck/public-contracts/shopdeck-schematic-public-contract.md"
    )

def resolve_concept_to_schema(conn, semantic_key: str):
    """
    Helper function replicating how Brain Core / AZM resolves a semantic intent
    into its physical schema representation without hardcoded knowledge.
    """
    cursor = conn.execute(
        """
        SELECT c.semantic_key, r.ref_name, a.field_name
        FROM azm_concepts c
        JOIN azm_attr_mappings m ON m.concept_id = c.id
        JOIN azm_schematic_attrs a ON a.id = m.schematic_attr_id
        JOIN azm_schematic_refs r ON r.id = a.schematic_ref_id
        WHERE c.semantic_key = ?
        """,
        (semantic_key,)
    )
    return cursor.fetchall()

def test_ndr_resolution():
    conn = get_connection()
    res = resolve_concept_to_schema(conn, "shopdeck.event.delivery_exception.reason")
    assert len(res) > 0, "NDR reason should resolve to a physical field"
    
    found = False
    for r in res:
        if r["ref_name"] == "vw_shopdeck_shipment_ndr_reports" and r["field_name"] == "latest_ndr_reason":
            found = True
            break
    assert found, f"Expected vw_shopdeck_shipment_ndr_reports.latest_ndr_reason, got {res}"

def test_accounting_resolution():
    conn = get_connection()
    res = resolve_concept_to_schema(conn, "shopdeck.entity.order.gross_value")
    assert len(res) > 0, "Accounting gross value should resolve to a physical field"
    found = False
    for r in res:
        if r["ref_name"] == "vw_shopdeck_order_summary" and r["field_name"] == "total_amount":
            found = True
            break
    assert found, f"Expected vw_shopdeck_order_summary.total_amount, got {res}"

def test_customer_query_resolution():
    conn = get_connection()
    res = resolve_concept_to_schema(conn, "shopdeck.entity.customer")
    assert len(res) > 0, "Customer query should resolve to a physical field"
    # customer_id appears in multiple views
    views = [r["ref_name"] for r in res]
    assert "vw_shopdeck_customer_info" in views
    assert "vw_shopdeck_order_line_items" in views

def test_inventory_resolution():
    conn = get_connection()
    res = resolve_concept_to_schema(conn, "shopdeck.entity.order_quantity")
    assert len(res) > 0, "Inventory query should resolve to a physical field"
    found = False
    for r in res:
        if r["ref_name"] == "vw_shopdeck_order_line_items" and r["field_name"] == "quantity":
            found = True
            break
    assert found, f"Expected vw_shopdeck_order_line_items.quantity, got {res}"

def test_external_channel_mapping():
    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT native.semantic_key as native_key, m.external_system, m.external_key
        FROM azm_external_mappings m
        JOIN azm_concepts native ON m.aaram_native_concept_id = native.id
        """
    )
    res = cursor.fetchall()
    found = False
    for r in res:
        if r["native_key"] == "catalog.entity.sku" and r["external_system"] == "shopdeck" and r["external_key"] == "customer_sku_short_id":
            found = True
            break
    assert found, "External channel mapping for customer_sku_short_id should map to catalog.entity.sku"
    
    # Assert Catalog is still AARAM_NATIVE
    ns_cursor = conn.execute("SELECT classification FROM azm_namespaces WHERE name = 'catalog'")
    assert ns_cursor.fetchone()["classification"] == "AARAM_NATIVE"
    
    # Assert ShopDeck is EXTERNAL_CHANNEL
    ns_cursor = conn.execute("SELECT classification FROM azm_namespaces WHERE name = 'shopdeck'")
    assert ns_cursor.fetchone()["classification"] == "EXTERNAL_CHANNEL"
