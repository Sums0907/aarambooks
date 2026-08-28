import pytest
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse

@pytest.fixture
def mock_brain():
    return AsyncMock()

@pytest.fixture
def mock_gateway():
    return AsyncMock()

@pytest.fixture
def mock_knowledge():
    k = MagicMock()
    k.get_certified_capabilities.return_value = []
    k.get_unsupported_policies.return_value = []
    return k

@pytest.mark.asyncio
async def test_clarification_required(mock_brain, mock_gateway, mock_knowledge):
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content='''```json
        {
            "status": "CLARIFICATION_REQUIRED",
            "reason": "Ask the user what quantity or rule to use for 'low stock'."
        }
        ```''',
        model_used="mock", prompt_tokens=10, completion_tokens=15
    )
    
    answer = await orchestrator.handle_query("Which items are low stock?", "user_123")
    
    assert "Clarification needed: Ask the user what quantity" in answer
    mock_brain.execute_requirements.assert_not_called()
