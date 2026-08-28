from typing import List

from src.shared.semantic_resolution_contracts import DomainSemanticKnowledge, SemanticConcept
from src.shared.azm.interfaces import AzmProvider

class InventorySemanticKnowledge(DomainSemanticKnowledge):
    """
    The runtime adapter that projects Inventory-relevant Azm knowledge to Brain Core.
    """
    def __init__(self, azm: AzmProvider):
        self._azm = azm
        self._namespace = "inventory"

    def search_concepts(self, query: str) -> List[SemanticConcept]:
        inventory_concepts = self._azm.search_concepts_by_namespace(self._namespace, query)
        generic_concepts = self._azm.search_concepts_by_namespace("generic", query)
        return inventory_concepts + generic_concepts

    def get_certified_capabilities(self) -> List[SemanticConcept]:
        all_concepts = getattr(self._azm, "_concepts", [])
        return [c for c in all_concepts if c.concept_id.startswith(self._namespace) and c.concept_type == "CAPABILITY"]
        
    def get_unsupported_policies(self) -> List[SemanticConcept]:
        all_concepts = getattr(self._azm, "_concepts", [])
        return [c for c in all_concepts if c.concept_id.startswith(self._namespace) and c.concept_type == "POLICY" and (c.metadata or {}).get("status") == "UNSUPPORTED"]
        
    def get_certified_policies(self) -> List[SemanticConcept]:
        all_concepts = getattr(self._azm, "_concepts", [])
        return [c for c in all_concepts if c.concept_id.startswith(self._namespace) and c.concept_type == "POLICY" and (c.metadata or {}).get("status") != "UNSUPPORTED"]
