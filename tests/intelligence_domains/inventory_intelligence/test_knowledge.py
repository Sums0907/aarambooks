import pytest

from src.azm.provider import GlobalAzmProvider
from src.intelligence_domains.inventory_intelligence.knowledge import InventorySemanticKnowledge
from src.shared.cognitive_planning_contracts import EvidenceRequirement
from src.brain_core.semantics.resolver import GenericSemanticResolver
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement

@pytest.fixture
def azm():
    return GlobalAzmProvider()

@pytest.fixture
def knowledge(azm):
    return InventorySemanticKnowledge(azm)

@pytest.fixture
def resolver(knowledge):
    return GenericSemanticResolver(knowledge)

def test_certified_vocabulary_retrieval(azm):
    """1. Certified vocabulary retrieval."""
    results = azm.search_concepts_by_namespace("inventory", "warehouse")
    assert len(results) >= 1
    assert any(c.concept_id == "inventory.entity.warehouse" for c in results)

def test_natural_language_semantic_mapping(resolver):
    """2. Natural-language semantic mapping (e.g. 'history' -> ledger capability)."""
    req = EvidenceRequirement(
        requirement_id="req-1",
        semantic_description="Show me the movement history of SKU X",
        rationale="test"
    )
    resolved = resolver.resolve(req)
    identities = [c.identity for c in resolved.semantic_constraints]
    
    assert "inventory.capability.ledger" in identities
    assert "inventory.vocabulary.ledger" in identities
    assert "inventory.entity.sku" in identities

def test_correct_capability_urn_resolution_and_constraints(azm):
    """3, 4, 5. Correct URN resolution and constraint recognition."""
    ledger_cap = azm.get_concept_by_id("inventory.capability.ledger")
    
    assert ledger_cap.metadata is not None
    assert ledger_cap.metadata["urn"] == "urn:aarambooks:inventory:capability:ledger"
    assert "inventory.entity.sku" in ledger_cap.metadata["required_constraints"]
    assert "inventory.temporal.posting_date" in ledger_cap.metadata["optional_constraints"]

def test_unsupported_concept_handling(resolver):
    """6, 7. Unsupported concept handling & No invention of policies."""
    req = EvidenceRequirement(
        requirement_id="req-2",
        semantic_description="Which SKUs are running low on stock? Show me the valuation.",
        rationale="test"
    )
    resolved = resolver.resolve(req)
    identities = [c.identity for c in resolved.semantic_constraints]
    
    # "stock" hits balance capability, but "low" and "valuation" should NOT map to anything
    assert "inventory.states.low_stock" not in identities
    assert "inventory.attribute.valuation" not in identities
    assert "inventory.capability.balance" in identities

def test_azm_provider_interaction(knowledge):
    """8, 9. AzmProvider interaction."""
    results = knowledge.search_concepts("missing stock")
    identities = [c.concept_id for c in results]
    assert "inventory.vocabulary.exception" in identities
    assert "inventory.capability.exception_status" in identities

def test_brain_core_consumes_projected_knowledge(resolver):
    """Ensure generic resolver doesn't generate physical logic."""
    req = EvidenceRequirement(
        requirement_id="req-1",
        semantic_description="What is the stock of book X in store Y?",
        rationale="test"
    )
    resolved = resolver.resolve(req)
    identities = [c.identity for c in resolved.semantic_constraints]
    
    assert "inventory.capability.balance" in identities
    
    for constraint in resolved.semantic_constraints:
        assert not hasattr(constraint, "parameter_name")
        assert not hasattr(constraint, "value")
        assert not hasattr(constraint, "physical_reference")
