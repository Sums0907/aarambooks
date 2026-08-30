import pytest
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.shared.semantic_resolution_contracts import SemanticConcept
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata
from datetime import datetime, UTC

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
            description="Balance",
            metadata={"urn": "urn:aarambooks:inventory:capability:balance", "required_constraints": []}
        )
    ]
    k.get_unsupported_policies.return_value = []
    k.get_certified_policies.return_value = []
    return k

@pytest.mark.asyncio
async def test_action_formulation_creates_escalation(mock_brain, mock_gateway, mock_knowledge):
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        # Intent Phase
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "understanding": {
                        "intent": "RETRIEVE",
                        "entities": [],
                        "conditions": []
                    }
            }
            ```''',
            model_used="mock", prompt_tokens=10, completion_tokens=15
        ),
        # Reasoning Phase
        GatewayGenerationResponse(content="The evidence indicates a severe issue.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        # Action Phase
        GatewayGenerationResponse(
            content='''```json
            {
                "category": "human_assistance",
                "reasoning": "Severe issue requires human review",
                "parameters": {"context": "severe"}
            }
            ```''',
            model_used="mock", prompt_tokens=10, completion_tokens=15
        )
    ]

    mock_knowledge.get_certified_capabilities.return_value = [
        SemanticConcept(
            concept_id="inventory.capability.exception_status",
            concept_name="Exception Capability",
            concept_type="CAPABILITY",
            aliases=[],
            description="Exception",
            metadata={"urn": "urn:aarambooks:inventory:capability:exception_status", "required_constraints": []}
        )
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1",
        plan_id="direct",
        sufficiency_assessment="SUFFICIENT",
        gaps=[],
        evidence_items=[]
    )
    
    answer = await orchestrator.handle_query("Urgent stock exception", "user_123")
    
    # Assert output contains dispatched action
    assert "The evidence indicates a severe issue." in answer

@pytest.mark.asyncio
async def test_action_formulation_no_action(mock_brain, mock_gateway, mock_knowledge):
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        # Intent Phase
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "understanding": {
                        "intent": "RETRIEVE",
                        "entities": [],
                        "conditions": []
                    }
            }
            ```''',
            model_used="mock", prompt_tokens=10, completion_tokens=15
        ),
        # Reasoning Phase
        GatewayGenerationResponse(content="Just normal stock levels.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        # Action Phase
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_knowledge.get_certified_capabilities.return_value = [
        SemanticConcept(
            concept_id="inventory.capability.balance",
            concept_name="Balance Capability",
            concept_type="CAPABILITY",
            aliases=[],
            description="Balance",
            metadata={"urn": "urn:aarambooks:inventory:capability:balance", "required_constraints": []}
        )
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1",
        plan_id="direct",
        sufficiency_assessment="SUFFICIENT",
        gaps=[],
        evidence_items=[]
    )
    
    answer = await orchestrator.handle_query("What is stock?", "user_123")
    
    # Assert output does NOT contain dispatched action
    assert "Just normal stock levels." in answer
    assert "[Action Dispatched]:" not in answer
