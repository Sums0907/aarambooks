import pytest
import json
from unittest.mock import MagicMock, AsyncMock

from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
from src.shared.conversational_contracts import MultimodalQuery
from src.intelligence_domains.catalog_intelligence.models import CatalogIntent, ProposedCatalogAction

class DummyGatewayProvider:
    def __init__(self, mocked_content: str):
        self.mocked_content = mocked_content

    async def generate(self, req):
        class Resp:
            content = self.mocked_content
        return Resp()

class DummyCEMResolver:
    def __init__(self, scenario: str):
        self.scenario = scenario

    def resolve(self, domain):
        class MockCEM:
            async def verify_catalog_collision(self, draft):
                return {"scenario": self.scenario}
        return MockCEM()

@pytest.mark.asyncio
async def test_explicit_create_family_survives_scenario_d():
    """
    Test that explicit CREATE_FAMILY intent is not overwritten by Scenario D.
    """
    mock_content = json.dumps({
        "operation_intent": "CREATE_FAMILY",
        "draft_fields": {
            "product_name": {"value": "Test Product"}
        }
    })
    orchestrator = CatalogIntelligenceOrchestrator(
        memory_provider=AsyncMock(),
        azm_provider=AsyncMock(),
        sabaq_provider=AsyncMock(),
        gateway_provider=DummyGatewayProvider(mock_content),
        cem_resolver=DummyCEMResolver(scenario="D")
    )
    
    query = MultimodalQuery(text="Create a new test product")
    understanding = await orchestrator.extract_understanding(query)
    
    # Extract action from understanding
    action_json = None
    for param in understanding.parameters:
        if param.parameter_name == "action_json":
            action_json = param.value
            
    assert action_json is not None
    action = ProposedCatalogAction.model_validate_json(action_json)
    
    assert action.intent == CatalogIntent.CREATE_FAMILY
    assert action.is_confirmed is False

@pytest.mark.asyncio
async def test_explicit_non_create_intent_not_overwritten_by_scenario_d():
    """
    Test that explicit non-create intent (UPSERT_SKUS) is NOT overwritten by Scenario D.
    Scenario D is evidence/state only.
    """
    mock_content = json.dumps({
        "operation_intent": "UPSERT_SKUS",
        "draft_fields": {
            "product_name": {"value": "Test Product"}
        }
    })
    orchestrator = CatalogIntelligenceOrchestrator(
        memory_provider=AsyncMock(),
        azm_provider=AsyncMock(),
        sabaq_provider=AsyncMock(),
        gateway_provider=DummyGatewayProvider(mock_content),
        cem_resolver=DummyCEMResolver(scenario="D")
    )
    
    query = MultimodalQuery(text="Add to existing product")
    understanding = await orchestrator.extract_understanding(query)
    
    action_json = None
    for param in understanding.parameters:
        if param.parameter_name == "action_json":
            action_json = param.value
            
    assert action_json is not None
    action = ProposedCatalogAction.model_validate_json(action_json)
    
    assert action.intent == CatalogIntent.UPSERT_SKUS
    assert action.is_confirmed is False


@pytest.mark.asyncio
async def test_natural_language_info_preserved():
    """
    Test that product_name, colour, and size are preserved.
    """
    mock_content = json.dumps({
        "operation_intent": "CREATE_FAMILY",
        "draft_fields": {
            "product_name": {"value": "Midnight Blue Bedsheet"},
            "colour": {"value": "Midnight Blue"},
            "size": {"value": "King Size"}
        }
    })
    orchestrator = CatalogIntelligenceOrchestrator(
        memory_provider=AsyncMock(),
        azm_provider=AsyncMock(),
        sabaq_provider=AsyncMock(),
        gateway_provider=DummyGatewayProvider(mock_content),
        cem_resolver=DummyCEMResolver(scenario="D")
    )
    
    query = MultimodalQuery(text="Add a Midnight Blue bedsheet, king size")
    understanding = await orchestrator.extract_understanding(query)
    
    action_json = None
    for param in understanding.parameters:
        if param.parameter_name == "action_json":
            action_json = param.value
            
    assert action_json is not None
    action = ProposedCatalogAction.model_validate_json(action_json)
    
    assert action.draft.product_name.value == "Midnight Blue Bedsheet"
    assert action.draft.colour.value == "Midnight Blue"  # Should NOT be "BL"
    assert action.draft.size.value == "King Size"
    assert action.is_confirmed is False
