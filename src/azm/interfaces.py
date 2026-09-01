from typing import List
from typing_extensions import Protocol

from src.shared.semantic_resolution_contracts import SemanticConcept

class AzmProvider(Protocol):
    """
    The interface for accessing Azm, the ecosystem-wide proprietary intelligence asset.
    Azm owns the declarative definitions of WHAT concepts mean across the ecosystem.
    It does not contain operational rules, logic, or runtime context extraction.
    """
    
    def search_concepts_by_namespace(self, namespace: str, query: str) -> List[SemanticConcept]:
        """
        Search for semantic concepts within a specific domain namespace.
        (e.g., namespace="inventory.states", query="low stock")
        """
        ...
    
    def get_concept_by_id(self, concept_id: str) -> SemanticConcept:
        """
        Retrieve a specific concept definition by its unique identifier.
        """
        ...
    
    def get_namespace_schema(self, namespace: str) -> dict:
        """
        Retrieve the public read schemas (e.g. SQL views or MCP tool schemas)
        for the given namespace.
        """
        ...
