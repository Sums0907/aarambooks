from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from typing_extensions import Protocol

from src.shared.cognitive_planning_contracts import EvidenceRequirement

# ---------------------------------------------------------
# KNOWLEDGE (WHAT) - Provided by Intelligence Domain / Azm
# ---------------------------------------------------------

class SemanticConcept(BaseModel):
    """
    A persistent, declarative dictionary definition originating from Azm.
    This defines WHAT a concept means in the Aaram ecosystem.
    """
    concept_id: str  # e.g., "inventory.states.low_stock"
    concept_name: str
    concept_type: str # e.g., "ENTITY", "ATTRIBUTE", "STATE", "TEMPORAL", "AGGREGATION", "RELATIONSHIP"
    aliases: List[str] = []
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None # For provenance or additional generic context

class DomainSemanticKnowledge(Protocol):
    """
    The generic contract through which Brain Core requests declarative meaning.
    """
    def search_concepts(self, query: str) -> List[SemanticConcept]:
        ...

# ---------------------------------------------------------
# INFRASTRUCTURE OUTPUT (HOW) - Produced by Brain Core
# ---------------------------------------------------------

class SemanticConstraint(BaseModel):
    """
    A query-specific instantiation or interpretation of a concept.
    This forms the Resolved Requirement.
    """
    identity: str
    constraint_type: str # e.g., "ENTITY", "STATE", "ATTRIBUTE", "TEMPORAL"
    operator: str = "EQUALS"
    bound_value: Optional[str] = None

class ResolvedSemanticRequirement(BaseModel):
    """
    The output of the Semantic Resolution Infrastructure.
    Contains the original requirement plus any semantic constraints discovered.
    Notice: It does NOT contain Target Capability.
    """
    requirement_id: str
    original_requirement: EvidenceRequirement
    core_identities: set[str] = set()
    semantic_constraints: List[SemanticConstraint] = []
    semantic_gaps: List[str] = []
