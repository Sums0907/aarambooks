from src.shared.semantic_resolution_contracts import SemanticConcept

# Inventory Domain Concepts
INVENTORY_CONCEPTS = [
    # Entities
    SemanticConcept(
        concept_id="inventory.entity.sku",
        concept_name="SKU",
        concept_type="ENTITY",
        aliases=["sku", "item", "product", "book"],
        description="A unique stock-keeping unit representing a physical product."
    ),
    SemanticConcept(
        concept_id="inventory.entity.warehouse",
        concept_name="Warehouse",
        concept_type="ENTITY",
        aliases=["warehouse", "location", "facility", "store"],
        description="A physical location owned by Aaram where goods are stored."
    ),
    SemanticConcept(
        concept_id="inventory.entity.jobwork_vendor",
        concept_name="Jobworker / Vendor",
        concept_type="ENTITY",
        aliases=["jobworker", "vendor", "supplier", "tailor"],
        description="A third-party partner who holds Aaram raw materials for assembly."
    ),
    SemanticConcept(
        concept_id="inventory.temporal.posting_date",
        concept_name="Posting Date",
        concept_type="TEMPORAL",
        aliases=["date", "posting date", "when"],
        description="The date a movement was posted to the ledger."
    ),
    
    # Vocabularies
    SemanticConcept(
        concept_id="inventory.vocabulary.balance",
        concept_name="Balance / Availability",
        concept_type="VOCABULARY",
        aliases=["availability", "on hand", "balance", "stock", "allocated"],
        description="Quantity on hand or allocated."
    ),
    SemanticConcept(
        concept_id="inventory.vocabulary.ledger",
        concept_name="Ledger / Movement",
        concept_type="VOCABULARY",
        aliases=["history", "movement history", "transactions", "in/out"],
        description="Historical stock movements in and out."
    ),
    
    # Capabilities (CEM Mutations)
    SemanticConcept(
        concept_id="inventory.capability.adjust_balance",
        concept_name="Adjust Balance",
        concept_type="CAPABILITY",
        aliases=["adjust", "fix stock", "update balance"],
        description="Transactionally adjust the stock balance.",
        metadata={
            "urn": "urn:aarambooks:inventory:capability:adjust_balance",
            "required_constraints": ["inventory.entity.sku"],
        }
    )
]

# Public Read Contracts (SQL Views)
INVENTORY_PUBLIC_VIEWS = {
    "vw_stock_balances": {
        "description": "Current stock balances for all SKUs across all warehouses.",
        "columns": {
            "sku": "STRING - Product SKU",
            "item_name": "STRING - Name of product",
            "on_hand_quantity": "INTEGER - Physical stock in warehouse",
            "available_quantity": "INTEGER - Physical stock minus allocated/reserved",
            "warehouse": "STRING - Warehouse location code"
        }
    },
    "vw_bom_components": {
        "description": "Bill of Materials (BOM) components required to build a parent SKU.",
        "columns": {
            "parent_sku": "STRING - The finished good SKU",
            "component_sku": "STRING - The raw material SKU",
            "component_name": "STRING - Name of the raw material",
            "quantity_required": "FLOAT - Amount needed per parent item",
            "uom": "STRING - Unit of measure"
        }
    },
    "vw_jobwork_status": {
        "description": "Current pending stock held by external jobworkers (vendors/tailors).",
        "columns": {
            "vendor_id": "STRING - Unique vendor identifier",
            "vendor_name": "STRING - Name of the vendor",
            "sku": "STRING - Item held by vendor",
            "pending_quantity": "INTEGER - Quantity still pending return",
            "issue_date": "TIMESTAMP - Date materials were issued"
        }
    },
    "vw_suppliers": {
        "description": "List of approved suppliers/vendors.",
        "columns": {
            "supplier_id": "STRING - Supplier identifier",
            "supplier_name": "STRING - Supplier name",
            "item_sku": "STRING - SKU supplied by this vendor",
            "lead_time_days": "INTEGER - Standard lead time"
        }
    }
}
