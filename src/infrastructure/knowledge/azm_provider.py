from typing import List

from src.shared.azm.interfaces import AzmProvider
from src.shared.semantic_resolution_contracts import SemanticConcept

class InMemoryAzmProvider(AzmProvider):
    """
    A minimal, in-memory implementation of Azm for Stage D proof-of-concept.
    This simulates an external, ecosystem-wide knowledge base.
    """
    def __init__(self):
        # The central dictionary of ALL ecosystem concepts.
        self._concepts = [
            # Entities & Vocabulary
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
            SemanticConcept(
                concept_id="inventory.temporal.exception_date",
                concept_name="Exception Date",
                concept_type="TEMPORAL",
                aliases=["exception date", "discrepancy date"],
                description="The date an exception was recorded."
            ),
            
            # Derived Vocabulary
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
            SemanticConcept(
                concept_id="inventory.vocabulary.jobwork_custody",
                concept_name="Job Work Custody",
                concept_type="VOCABULARY",
                aliases=["what does vendor hold", "pending with vendor", "job worker stock", "issued", "consumed", "returned"],
                description="Stock held by vendor, including issued, consumed, returned, and pending."
            ),
            SemanticConcept(
                concept_id="inventory.vocabulary.pending_return",
                concept_name="Pending Return",
                concept_type="VOCABULARY",
                aliases=["pending return", "pending"],
                description="Remaining raw materials awaiting finished goods receipt from a jobworker."
            ),
            SemanticConcept(
                concept_id="inventory.vocabulary.exception",
                concept_name="Exception / Discrepancy",
                concept_type="VOCABULARY",
                aliases=["missing stock", "mismatch", "discrepancy", "exception", "count error"],
                description="Mismatches between expected and actual quantities."
            ),
            SemanticConcept(
                concept_id="inventory.vocabulary.confidence_score",
                concept_name="Confidence Score",
                concept_type="VOCABULARY",
                aliases=["confidence", "reliability"],
                description="System-generated metric of stock data reliability."
            ),

            # Capabilities & Constraint Mappings
            SemanticConcept(
                concept_id="inventory.capability.balance",
                concept_name="Balance Capability",
                concept_type="CAPABILITY",
                aliases=["how much", "do we have", "stock", "availability", "on hand", "balance"],
                description="Current stock balance.",
                metadata={
                    "urn": "urn:aarambooks:inventory:capability:balance",
                    "required_constraints": ["inventory.entity.sku"],
                    "optional_constraints": ["inventory.entity.warehouse"]
                }
            ),
            SemanticConcept(
                concept_id="inventory.capability.ledger",
                concept_name="Ledger Capability",
                concept_type="CAPABILITY",
                aliases=["show history", "movement history", "transactions", "in/out"],
                description="Historical stock movements.",
                metadata={
                    "urn": "urn:aarambooks:inventory:capability:ledger",
                    "required_constraints": ["inventory.entity.sku"],
                    "optional_constraints": ["inventory.temporal.posting_date"]
                }
            ),
            SemanticConcept(
                concept_id="inventory.capability.jobwork_status",
                concept_name="Jobwork Status Capability",
                concept_type="CAPABILITY",
                aliases=["what does vendor hold", "pending with vendor", "job worker stock", "issued", "consumed", "returned"],
                description="Stock held by vendor.",
                metadata={
                    "urn": "urn:aarambooks:inventory:capability:jobwork_status",
                    "required_constraints": ["inventory.entity.jobwork_vendor"],
                    "optional_constraints": ["inventory.entity.sku"]
                }
            ),
            SemanticConcept(
                concept_id="inventory.capability.exception_status",
                concept_name="Exception Status Capability",
                concept_type="CAPABILITY",
                aliases=["missing stock", "mismatch", "discrepancy", "exception", "count error"],
                description="Active discrepancies.",
                metadata={
                    "urn": "urn:aarambooks:inventory:capability:exception_status",
                    "required_constraints": ["inventory.entity.sku"],
                    "optional_constraints": ["inventory.temporal.exception_date"]
                }
            ),

            # Policies
            SemanticConcept(
                concept_id="inventory.policy.unique_balance",
                concept_name="Unique Stock Keeping",
                concept_type="POLICY",
                aliases=["unique balance"],
                description="Balances require both SKU and Warehouse to be definitively resolved."
            ),
            SemanticConcept(
                concept_id="inventory.policy.immutable_movement",
                concept_name="Movement Immutability",
                concept_type="POLICY",
                aliases=["immutable movement"],
                description="Ledger movements are immutable once posted."
            ),
            SemanticConcept(
                concept_id="inventory.policy.exception_source",
                concept_name="Exception Source",
                concept_type="POLICY",
                aliases=["exception source"],
                description="Exceptions specify a source system."
            ),
            SemanticConcept(
                concept_id="inventory.policy.jobwork_lifecycle",
                concept_name="Job Work Lifecycle",
                concept_type="POLICY",
                aliases=["job work lifecycle"],
                description="Job work tracks Issued -> Consumed/Returned -> Pending."
            ),
            SemanticConcept(
                concept_id="inventory.policy.confidence_score",
                concept_name="Confidence Score Policy",
                concept_type="POLICY",
                aliases=["confidence policy"],
                description="Balance records contain a system-generated confidence score."
            ),
            # Unsupported Policies
            SemanticConcept(
                concept_id="inventory.policy.unsupported.low_stock",
                concept_name="Low Stock Threshold",
                concept_type="POLICY",
                aliases=["low stock", "running low"],
                description="Low stock thresholds.",
                metadata={"status": "UNSUPPORTED"}
            ),
            SemanticConcept(
                concept_id="inventory.policy.unsupported.reorder",
                concept_name="Reorder Policy",
                concept_type="POLICY",
                aliases=["reorder", "reorder threshold", "when to buy"],
                description="Reorder threshold rules.",
                metadata={"status": "UNSUPPORTED"}
            ),
            SemanticConcept(
                concept_id="inventory.policy.unsupported.valuation",
                concept_name="Valuation Policy",
                concept_type="POLICY",
                aliases=["valuation", "cogs", "inventory value", "worth"],
                description="Automated valuation / COGS logic.",
                metadata={"status": "UNSUPPORTED"}
            ),
            SemanticConcept(
                concept_id="inventory.policy.unsupported.aging",
                concept_name="Aging Policy",
                concept_type="POLICY",
                aliases=["aging", "overdue", "older than", "30 days"],
                description="Jobwork aging or SLA thresholds.",
                metadata={"status": "UNSUPPORTED"}
            ),
            SemanticConcept(
                concept_id="inventory.policy.unsupported.negative_stock",
                concept_name="Negative Stock Severity",
                concept_type="POLICY",
                aliases=["negative stock severity", "severity", "critical exception"],
                description="Severity mapping for exceptions.",
                metadata={"status": "UNSUPPORTED"}
            ),
        ]

    def search_concepts_by_namespace(self, namespace: str, query: str) -> List[SemanticConcept]:
        results = []
        for c in self._concepts:
            if c.concept_id.startswith(namespace):
                if c.concept_name.lower() in query.lower() or any(a.lower() in query.lower() for a in c.aliases):
                    results.append(c)
        return results

    def get_concept_by_id(self, concept_id: str) -> SemanticConcept:
        for c in self._concepts:
            if c.concept_id == concept_id:
                return c
        raise KeyError(f"Concept {concept_id} not found in Azm.")
