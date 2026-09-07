import pytest
from src.intelligence_domains.catalog_intelligence.models import FieldProvenance, CatalogDraft, DraftField, ProposedCatalogAction
from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.shared.conversational_contracts import MultimodalQuery
import json

class MockSabaqProvider:
    def __init__(self, historical_value="33", id_found=True):
        self.historical_value = historical_value
        self.id_found = id_found

    async def retrieve_evidence(self, *args, **kwargs):
        # Simulate FTS returning nothing to prove get_evidence is called
        return []

    async def get_evidence(self, id: str):
        if not self.id_found:
            return None
        
        class MockEvidence:
            def __init__(self, ev_id, h_val):
                self.id = ev_id
                self.evidence_data = {}
                self.context = {}
                self.provenance = "mock"
                self.confidence_score = 1.0
                self.created_at = "mock"
                self.expires_at = None
                self.structured_payload = {
                    "Product Code": "PC-1",
                    "Size": "72x78 + 12\"",
                    "Packaging Length (in cm)": h_val,
                    "Packaging Breadth (in cm)": 27.0,
                    "Packaging Height (in cm)": 11.0,
                    "Packaging Weight (in kg)": 1.3,
                    "MRP": 2999
                }
        return MockEvidence(id, self.historical_value)

class MockGateway:
    def __init__(self, weight=1.3, selling=1499, cost=700, mrp=2999):
        self.weight = weight
        self.selling = selling
        self.cost = cost
        self.mrp = mrp
        
    async def generate(self, req):
        payload = {
            "product_code": {"value": "PC-1", "candidate_sabaq_reference_id": "test_id"},
            "size": {"value": "72x78 + 12\"", "candidate_sabaq_reference_id": "test_id"},
            "packaging_length_cm": {"value": 33.0, "candidate_sabaq_reference_id": "test_id"},
            "packaging_breadth_cm": {"value": 27.0, "candidate_sabaq_reference_id": "test_id"},
            "packaging_height_cm": {"value": 11.0, "candidate_sabaq_reference_id": "test_id"},
            "packaging_weight_kg": {"value": self.weight, "candidate_sabaq_reference_id": "test_id"},
            "mrp": {"value": self.mrp, "candidate_sabaq_reference_id": "test_id"},
            "selling_price": {"value": self.selling, "candidate_sabaq_reference_id": "test_id"},
            "cost_price": {"value": self.cost, "candidate_sabaq_reference_id": "test_id"},
        }
        return GatewayGenerationResponse(
            content=json.dumps(payload),
            model_used="mock",
            prompt_tokens=0,
            completion_tokens=0
        )

class MockCemAdapter:
    def __init__(self, exists=True):
        self.exists = exists
        
    async def verify_business_state(self, req):
        class MockResponse:
            evidence_data = {"exists": self.exists, "active": True, "product_internal_id": "test_id", "product_code": "PC-1"} if (req.verification_target == "product_code" and self.exists) else {"exists": False}
        return MockResponse()

class MockCemResolver:
    def __init__(self, exists=True):
        self.exists = exists
    def resolve(self, domain): return MockCemAdapter(self.exists)


@pytest.mark.asyncio
async def test_deterministic_gateway_produces_ai_proposed():
    orch = CatalogIntelligenceOrchestrator(None)
    orch._gateway_provider = MockGateway()
    orch._evaluate_provenance_promotion = lambda *args, **kwargs: None
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.product_code.provenance == FieldProvenance.AI_PROPOSED
    assert draft.packaging_length_cm.provenance == FieldProvenance.AI_PROPOSED
    assert draft.packaging_length_cm.candidate_sabaq_reference_id == "test_id"

@pytest.mark.asyncio
async def test_scenario_b_mrp_blocked_without_policy():
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider())
    orch._gateway_provider = MockGateway()
    orch._cem_resolver = MockCemResolver(exists=True)
    orch._azm_provider = None
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.packaging_length_cm.provenance == FieldProvenance.SABAQ_REUSED
    assert draft.packaging_weight_kg.provenance == FieldProvenance.SABAQ_REUSED
    # MRP Blocked due to no azm_schema
    assert draft.mrp.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
    assert draft.selling_price.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
    assert draft.cost_price.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER

@pytest.mark.asyncio
async def test_scenario_b_mrp_promoted_with_policy():
    class MockAZMProvider:
        def get_namespace_schema(self, namespace):
            return {"uniform_mrp_policy": True}
            
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider(), azm_provider=MockAZMProvider())
    orch._gateway_provider = MockGateway()
    orch._cem_resolver = MockCemResolver(exists=True)
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.mrp.provenance == FieldProvenance.SABAQ_REUSED

@pytest.mark.asyncio
async def test_packaging_weight_blocked_when_outside_bounds():
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider())
    orch._gateway_provider = MockGateway(weight=50.0) # Outside bounds (10kg max)
    orch._cem_resolver = MockCemResolver(exists=True)
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.packaging_weight_kg.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER

@pytest.mark.asyncio
async def test_scenario_d_prevents_reuse():
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider())
    orch._gateway_provider = MockGateway()
    orch._cem_resolver = MockCemResolver(exists=False) # Scenario D
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.packaging_length_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
    assert draft.packaging_weight_kg.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
    assert draft.mrp.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER

@pytest.mark.asyncio
async def test_missing_candidate_evidence_rejected():
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider(id_found=False))
    orch._gateway_provider = MockGateway()
    orch._cem_resolver = MockCemResolver(exists=True)
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.packaging_length_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
    assert draft.firewall_diagnostics["packaging_length_cm"]["rejection_reason"] == "evidence-not-found"

@pytest.mark.asyncio
async def test_numeric_mismatch_rejected():
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider(historical_value="34.0"))
    orch._gateway_provider = MockGateway()
    orch._cem_resolver = MockCemResolver(exists=True)
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.packaging_length_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
    assert draft.firewall_diagnostics["packaging_length_cm"]["rejection_reason"] == "value-mismatch"

@pytest.mark.asyncio
async def test_numeric_match_accepted_string_integer():
    orch = CatalogIntelligenceOrchestrator(sabaq_provider=MockSabaqProvider(historical_value="33"))
    orch._gateway_provider = MockGateway() # MockGateway returns 33.0 for length
    orch._cem_resolver = MockCemResolver(exists=True)
    
    understanding = await orch.extract_understanding(MultimodalQuery(text="Query"))
    action = ProposedCatalogAction.model_validate_json(next(p.value for p in understanding.parameters if p.parameter_name == "action_json"))
    draft = action.draft
    
    assert draft.packaging_length_cm.provenance == FieldProvenance.SABAQ_REUSED
    assert draft.firewall_diagnostics["packaging_length_cm"]["rejection_reason"] == "sabaq-reused"
