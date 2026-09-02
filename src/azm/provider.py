from typing import List, Dict
import os
import logging

from src.azm.interfaces import AzmProvider
from src.shared.semantic_resolution_contracts import SemanticConcept
from src.azm.namespaces.inventory import INVENTORY_CONCEPTS, INVENTORY_PUBLIC_VIEWS
from src.azm.namespaces.ndr import NDR_CONCEPTS, NDR_PUBLIC_VIEWS
from src.azm.namespaces.shopdeck import SHOPDECK_CONCEPTS, SHOPDECK_PUBLIC_VIEWS

logger = logging.getLogger(__name__)


class GlobalAzmProvider(AzmProvider):
    """
    [DEPRECATED - BOOTSTRAP FALLBACK ONLY]
    The top-level container for Azm. 
    It federates across all domains to provide a unified semantic ontology and public schemas.
    """
    def __init__(self):
        self._concepts_by_namespace: Dict[str, List[SemanticConcept]] = {
            "inventory": INVENTORY_CONCEPTS,
            "ndr": NDR_CONCEPTS,
            "shopdeck": SHOPDECK_CONCEPTS
        }
        
        self._views_by_namespace: Dict[str, dict] = {
            "inventory": INVENTORY_PUBLIC_VIEWS,
            "ndr": NDR_PUBLIC_VIEWS,
            "shopdeck": SHOPDECK_PUBLIC_VIEWS
        }

    def search_concepts_by_namespace(self, namespace: str, query: str) -> List[SemanticConcept]:
        if namespace not in self._concepts_by_namespace:
            raise ValueError(f"Unknown namespace: {namespace}")
            
        concepts = self._concepts_by_namespace[namespace]
        query_lower = query.lower()
        
        results = []
        for concept in concepts:
            if query_lower in concept.concept_name.lower() or any(query_lower in alias.lower() for alias in concept.aliases):
                results.append(concept)
        return results

    def get_concept_by_id(self, concept_id: str) -> SemanticConcept:
        for concepts in self._concepts_by_namespace.values():
            for concept in concepts:
                if concept.concept_id == concept_id:
                    return concept
        raise ValueError(f"Concept {concept_id} not found in Azm")

    def get_namespace_schema(self, namespace: str) -> dict:
        if namespace not in self._views_by_namespace:
            raise ValueError(f"Unknown namespace: {namespace}")
        return self._views_by_namespace[namespace]


class AzmProviderFactory:
    """
    Factory for instantiating the correct AZM Provider.
    Prefers the PersistentAzmProvider if the DB is available and initialized.
    Falls back to the deprecated GlobalAzmProvider (bootstrap) if not.
    """
    @staticmethod
    def create(db_url: str = None) -> AzmProvider:
        # Check if we should try the persistent provider
        from src.azm.config import AZM_DATABASE_URL
        target_url = db_url or AZM_DATABASE_URL
        
        if target_url:
            try:
                from src.azm.persistent_provider import PersistentAzmProvider
                fallback = GlobalAzmProvider()
                provider = PersistentAzmProvider(target_url, legacy_fallback=fallback)
                return provider
            except Exception as e:
                logger.warning(f"AZM persistent provider unavailable ({e}). Falling back to bootstrap.")
        
        return GlobalAzmProvider()
