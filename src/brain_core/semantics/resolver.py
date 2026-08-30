import uuid
from typing import List

from src.shared.cognitive_planning_contracts import EvidenceRequirement
from src.shared.semantic_resolution_contracts import (
    DomainSemanticKnowledge,
    ResolvedSemanticRequirement,
    SemanticConstraint,
    SemanticConcept
)

class GenericSemanticResolver:
    """
    Brain Core infrastructure for Semantic Resolution.
    It translates an EvidenceRequirement into query-bound SemanticConstraints
    using the declarative DomainSemanticKnowledge provided by Azm/Domain.
    """
    def __init__(self, knowledge: DomainSemanticKnowledge):
        self._knowledge = knowledge

    def resolve(self, requirement: EvidenceRequirement | ResolvedSemanticRequirement) -> ResolvedSemanticRequirement:
        if isinstance(requirement, ResolvedSemanticRequirement):
            return requirement
            
        resolved_req = ResolvedSemanticRequirement(
            requirement_id=requirement.requirement_id,
            original_requirement=requirement,
            semantic_constraints=[],
            semantic_gaps=[]
        )

        desc = requirement.semantic_description.lower()
        
        # 1. Search knowledge for concepts based on NLP text matching
        concepts = self._knowledge.search_concepts(desc)
        
        if not concepts:
            resolved_req.semantic_gaps.append(f"No semantic concepts found in knowledge for: '{desc}'")
            return resolved_req
            
        # 2. Translate persistent SemanticConcepts into query-bound SemanticConstraints
        for concept in concepts:
            # We simply bind the concept to a constraint indicating it is present in the query.
            # No physical parameters, SQL, or API values are assumed.
            constraint = SemanticConstraint(
                identity=concept.concept_id,
                constraint_type=concept.concept_type,
                operator="EQUALS",
                bound_value=None  # A full implementation would use NER here to extract values if present
            )
            resolved_req.semantic_constraints.append(constraint)

        return resolved_req
