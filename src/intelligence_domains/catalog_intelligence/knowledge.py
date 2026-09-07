from typing import Optional, List, Dict
from src.azm.interfaces import AzmProvider
from src.shared.semantic_resolution_contracts import SemanticConcept


class CatalogSemanticKnowledge:
    """
    Adapter bridging Catalog Intelligence Domain to the AZM Persistent Database.
    
    This class MUST ONLY retrieve knowledge through the provided AzmProvider.
    It MUST NOT connect to the Catalog DB, nor import Catalog Python logic.
    """
    def __init__(self, azm_provider: AzmProvider):
        self._azm = azm_provider

    def get_product_concept(self) -> SemanticConcept:
        """
        Retrieves the canonical semantic definition of a 'Product' from AZM.
        """
        return self._azm.get_concept_by_id("catalog.entity.product")

    def get_sku_concept(self) -> SemanticConcept:
        """
        Retrieves the canonical semantic definition of an 'SKU' from AZM.
        """
        return self._azm.get_concept_by_id("catalog.entity.sku")

    def search_catalog_concepts(self, query: str) -> List[SemanticConcept]:
        """
        Searches all Catalog semantic concepts (e.g. by alias or name).
        """
        return self._azm.search_concepts_by_namespace("catalog", query)

    def get_catalog_views(self) -> dict:
        """
        Retrieves the Schematic Public Contract (the available views/fields) from AZM.
        """
        return self._azm.get_namespace_schema("catalog")

    def get_schematic_attribute(self, view_name: str, field_name: str) -> Optional[dict]:
        """
        Retrieves specific field-level knowledge (type, description, derivations, mappings).
        """
        return self._azm.get_schematic_attr("catalog", view_name, field_name)
