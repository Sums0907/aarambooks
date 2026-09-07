"""
Catalog Intelligence Domain (Catalog ID)

This domain is responsible for the cognitive intake, extraction, and resolution
of Catalog information. It parses unstructured inputs and reasons about
product families and SKUs. 

It THINKS & PROPOSES.
It does NOT own canonical truth, enforce uniqueness, or mutate the database directly.
"""

from .knowledge import CatalogSemanticKnowledge
from .models import (
    DecisionStatus,
    AuthorizedContext,
    IntakeRequest,
    CandidateSKU,
    CandidateProduct,
    ResolutionDecision,
)
from .resolution import CognitiveResolutionEngine

__all__ = [
    "CatalogSemanticKnowledge",
    "DecisionStatus",
    "AuthorizedContext",
    "IntakeRequest",
    "CandidateSKU",
    "CandidateProduct",
    "ResolutionDecision",
    "CognitiveResolutionEngine",
]
