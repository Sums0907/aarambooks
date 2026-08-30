import pytest
from typing import List, Optional

from src.shared.cognitive_planning_contracts import EvidenceRequirement
from src.shared.semantic_resolution_contracts import (
    DomainSemanticKnowledge,
    SemanticConcept,
    ResolvedSemanticRequirement
)
from src.brain_core.semantics.resolver import GenericSemanticResolver

class MockGenericSemanticKnowledge(DomainSemanticKnowledge):
    """
    A synthetic Domain Semantic Knowledge provider for a generic domain.
    Proves that Brain Core is domain-agnostic and relies strictly on the SemanticConstraint model.
    """
    def __init__(self):
        self._concepts = [
            SemanticConcept(
                concept_id="generic.entity.person",
                concept_name="Person",
                concept_type="ENTITY",
                aliases=["individual", "human"],
                description="A human entity."
            ),
            SemanticConcept(
                concept_id="generic.state.urgent",
                concept_name="Urgent",
                concept_type="STATE",
                aliases=["immediate", "critical"]
            ),
            SemanticConcept(
                concept_id="generic.attribute.high_value",
                concept_name="High Value",
                concept_type="ATTRIBUTE",
                aliases=["expensive", "premium"]
            ),
            SemanticConcept(
                concept_id="generic.temporal.recent",
                concept_name="Recent",
                concept_type="TEMPORAL",
                aliases=["lately", "last 30 days"]
            ),
            SemanticConcept(
                concept_id="generic.aggregation.highest",
                concept_name="Highest",
                concept_type="AGGREGATION",
                aliases=["top", "maximum"]
            )
        ]

    def search_concepts(self, query: str) -> List[SemanticConcept]:
        results = []
        for c in self._concepts:
            if c.concept_name.lower() in query.lower() or any(a.lower() in query.lower() for a in c.aliases):
                results.append(c)
        return results

def test_generic_semantic_resolver_entity_resolution():
    knowledge = MockGenericSemanticKnowledge()
    resolver = GenericSemanticResolver(knowledge)
    
    req = EvidenceRequirement(
        requirement_id="req-1",
        semantic_description="Find that person",
        rationale="test"
    )
    
    resolved: ResolvedSemanticRequirement = resolver.resolve(req)
    
    assert resolved.requirement_id == "req-1"
    assert len(resolved.semantic_constraints) == 1
    assert resolved.semantic_constraints[0].constraint_type == "ENTITY"
    assert resolved.semantic_constraints[0].identity == "generic.entity.person"
    assert len(resolved.semantic_gaps) == 0

def test_generic_semantic_resolver_state_resolution():
    knowledge = MockGenericSemanticKnowledge()
    resolver = GenericSemanticResolver(knowledge)
    
    req = EvidenceRequirement(
        requirement_id="req-2",
        semantic_description="This is critical",
        rationale="test"
    )
    
    resolved: ResolvedSemanticRequirement = resolver.resolve(req)
    
    assert len(resolved.semantic_constraints) == 1
    assert resolved.semantic_constraints[0].constraint_type == "STATE"
    assert resolved.semantic_constraints[0].identity == "generic.state.urgent"
    assert len(resolved.semantic_gaps) == 0

def test_generic_semantic_resolver_attribute_resolution():
    knowledge = MockGenericSemanticKnowledge()
    resolver = GenericSemanticResolver(knowledge)
    
    req = EvidenceRequirement(
        requirement_id="req-3",
        semantic_description="We need premium items",
        rationale="test"
    )
    
    resolved: ResolvedSemanticRequirement = resolver.resolve(req)
    
    assert len(resolved.semantic_constraints) == 1
    assert resolved.semantic_constraints[0].constraint_type == "ATTRIBUTE"
    assert resolved.semantic_constraints[0].identity == "generic.attribute.high_value"
    assert len(resolved.semantic_gaps) == 0

def test_generic_semantic_resolver_temporal_and_aggregation():
    knowledge = MockGenericSemanticKnowledge()
    resolver = GenericSemanticResolver(knowledge)
    
    req = EvidenceRequirement(
        requirement_id="req-4",
        semantic_description="Show the highest recent activity",
        rationale="test"
    )
    
    resolved: ResolvedSemanticRequirement = resolver.resolve(req)
    
    # "highest" and "recent"
    assert len(resolved.semantic_constraints) == 2
    types = [c.constraint_type for c in resolved.semantic_constraints]
    assert "TEMPORAL" in types
    assert "AGGREGATION" in types
    assert len(resolved.semantic_gaps) == 0

def test_generic_semantic_resolver_no_concepts_found():
    knowledge = MockGenericSemanticKnowledge()
    resolver = GenericSemanticResolver(knowledge)
    
    req = EvidenceRequirement(
        requirement_id="req-5",
        semantic_description="Random unknown query about office chairs",
        rationale="test"
    )
    
    resolved: ResolvedSemanticRequirement = resolver.resolve(req)
    
    assert len(resolved.semantic_constraints) == 0
    assert len(resolved.semantic_gaps) == 1
    assert "No semantic concepts found" in resolved.semantic_gaps[0]

def test_no_physical_parameters_generated():
    knowledge = MockGenericSemanticKnowledge()
    resolver = GenericSemanticResolver(knowledge)
    
    req = EvidenceRequirement(
        requirement_id="req-6",
        semantic_description="Find top premium individual",
        rationale="test"
    )
    
    resolved: ResolvedSemanticRequirement = resolver.resolve(req)
    
    # Assert constraints exist but assert no ResolvedParameter or value mapping exists
    assert len(resolved.semantic_constraints) == 3
    for constraint in resolved.semantic_constraints:
        assert not hasattr(constraint, "value")
        assert not hasattr(constraint, "parameter_name")
        assert not hasattr(constraint, "physical_reference")
        # Ensure it purely contains the concept identities
        assert constraint.identity is not None
