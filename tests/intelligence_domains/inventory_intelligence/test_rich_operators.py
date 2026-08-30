import pytest
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.shared.semantic_resolution_contracts import SemanticConcept

@pytest.fixture
def mock_brain():
    return AsyncMock()

@pytest.fixture
def mock_gateway():
    return AsyncMock()

@pytest.fixture
def mock_knowledge():
    k = MagicMock()
    k.get_certified_capabilities.return_value = [
        SemanticConcept(
            concept_id="inventory.capability.balance",
            concept_name="Balance Capability",
            concept_type="CAPABILITY",
            aliases=[],
            metadata={"urn": "urn:aarambooks:inventory:capability:balance", "required_constraints": []}
        )
    ]
    return k

@pytest.mark.asyncio
async def test_unsupported_operator_rejection(mock_brain, mock_gateway, mock_knowledge):
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "understanding": {
                        "intent": "RETRIEVE",
                        "entities": [{"original_expression": "SKU1"}],
                        "conditions": [{"operator": "MAGIC_OPERATOR", "value": "SKU1"}]
                    }
            }
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        )
    ]
    
    answer = await orchestrator.handle_query("Show me balance", "user_123")
    assert "Input should be" in answer or "validation error" in answer

@pytest.mark.asyncio
async def test_valid_operator_acceptance(mock_brain, mock_gateway, mock_knowledge):
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "understanding": {
                        "intent": "RETRIEVE",
                        "entities": [],
                        "conditions": [{"operator": "GREATER_THAN", "value": "50"}]
                    }
            }
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        ),
        GatewayGenerationResponse(content="Data found.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]
    
    mock_brain.execute_requirements.return_value = MagicMock(sufficiency_assessment="SUFFICIENT", evidence_items=[])
    
    answer = await orchestrator.handle_query("Show me balance", "user_123")
    
    assert "Data found." in answer
    
    # Assert that the semantic constraint created has operator GREATER_THAN
    args, _ = mock_brain.execute_requirements.call_args
    req = args[0][0]
    
    assert len(req.semantic_constraints) == 2  # 1 for capability, 1 for constraint
    assert req.semantic_constraints[1].operator == "GREATER_THAN"
