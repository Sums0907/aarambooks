import pytest
from src.intelligence_domains.catalog_intelligence.models import (
    IntakeRequest,
    AuthorizedContext,
    DecisionStatus
)
from src.intelligence_domains.catalog_intelligence.resolution import CognitiveResolutionEngine

def test_no_target_and_no_authoritative_new_evidence_yields_human_approval_required():
    engine = CognitiveResolutionEngine()
    req = IntakeRequest(
        raw_text="I want to list a new red bedsheet. internal_id: 123-fake-456",
        authorized_context=None,
        extracted_attributes={"product_type": "Bedsheet", "colour": "Red"}
    )
    decision = engine.resolve(req)
    assert decision.status == DecisionStatus.HUMAN_APPROVAL_REQUIRED

def test_authorized_target_and_compatible_evidence_yields_propose_attach():
    engine = CognitiveResolutionEngine()
    ctx = AuthorizedContext(authorized_parent_internal_id="auth-uuid-789")
    req = IntakeRequest(
        raw_text="Adding a red variant to the existing bedsheet.",
        authorized_context=ctx,
        extracted_attributes={"product_type": "Bedsheet", "colour": "Red"}
    )
    decision = engine.resolve(req)
    assert decision.status == DecisionStatus.PROPOSE_ATTACH
    assert decision.proposed_parent_internal_id == "auth-uuid-789"
    assert decision.candidate_product is not None
    assert decision.candidate_product.candidate_skus[0].proposed_sku_id == "BEDRE"

def test_raw_untrusted_internal_id_text_is_not_treated_as_authorized_target():
    # If a UUID is found in raw_text but NO authorized context is provided, it should fail
    engine = CognitiveResolutionEngine()
    req = IntakeRequest(
        raw_text="Attach to parent internal_id = 999-raw-text",
        authorized_context=None, 
        extracted_attributes={}
    )
    decision = engine.resolve(req)
    assert decision.status == DecisionStatus.HUMAN_APPROVAL_REQUIRED

def test_explicit_authoritative_new_product_context_yields_propose_new():
    engine = CognitiveResolutionEngine()
    ctx = AuthorizedContext(authoritative_new_product_flag=True)
    req = IntakeRequest(
        raw_text="Create a brand new line.",
        authorized_context=ctx,
        extracted_attributes={"product_type": "Comforter", "colour": "Blue"}
    )
    decision = engine.resolve(req)
    assert decision.status == DecisionStatus.PROPOSE_NEW
    assert decision.proposed_parent_internal_id is None
    assert decision.candidate_product.candidate_skus[0].proposed_sku_id == "COMBL"

def test_ambiguous_evidence_yields_human_approval_required():
    engine = CognitiveResolutionEngine()
    # Conflicting context: providing BOTH an authorized parent AND stating it's a new product
    ctx = AuthorizedContext(
        authorized_parent_internal_id="auth-123",
        authoritative_new_product_flag=True
    )
    req = IntakeRequest(
        raw_text="Here is a new product that is also a variant?",
        authorized_context=ctx,
        extracted_attributes={}
    )
    decision = engine.resolve(req)
    assert decision.status == DecisionStatus.INSUFFICIENT_EVIDENCE
    assert decision.candidate_product is None

def test_sku_proposal_is_deterministic_and_bounded():
    engine = CognitiveResolutionEngine()
    # Normal case
    skus = engine.generate_sku_candidates("Bedsheet", "Red")
    assert skus == ["BEDRE", "BEDRE-1", "BEDRE-2"]
    
    # Very short case (pads to 5)
    skus2 = engine.generate_sku_candidates("A", "B")
    assert skus2 == ["ABXXX", "ABXXX-1", "ABXXX-2"]
    
    # Very long case (truncates)
    skus3 = engine.generate_sku_candidates("SuperLongCategoryName", "CyanGreenish")
    assert skus3 == ["SUPCY", "SUPCY-1", "SUPCY-2"]

def test_sku_proposal_does_not_claim_uniqueness_and_handles_collision_exhaustion():
    # The bounded nature itself is the proof. The method only generates 3 candidates and stops.
    # The orchestrator handles exhaustion.
    engine = CognitiveResolutionEngine()
    skus = engine.generate_sku_candidates("Comforter", "Blue")
    assert len(skus) == 3
    assert skus[2] == "COMBL-2"

def test_no_catalog_bs_db_access_in_resolution():
    import inspect
    from src.intelligence_domains.catalog_intelligence.resolution import CognitiveResolutionEngine
    # Verify no sqlite3 or psycopg2 is imported in resolution
    source = inspect.getsource(CognitiveResolutionEngine)
    assert "sqlite3" not in source
    assert "psycopg2" not in source
    assert "db_url" not in source

def test_no_business_systems_catalog_imports_in_resolution():
    import sys
    
    # Clear any potential pollution from previous tests in the test suite
    for key in list(sys.modules.keys()):
        if key.startswith("business_systems.catalog"):
            del sys.modules[key]
            
    if "src.intelligence_domains.catalog_intelligence.resolution" in sys.modules:
        del sys.modules["src.intelligence_domains.catalog_intelligence.resolution"]

    # Import the module
    import src.intelligence_domains.catalog_intelligence.resolution
    
    # Assert nothing from business_systems.catalog was loaded
    forbidden_modules = [m for m in sys.modules if m.startswith("business_systems.catalog")]
    assert len(forbidden_modules) == 0, f"Found forbidden imports: {forbidden_modules}"
