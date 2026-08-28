import pytest
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.shared.semantic_resolution_contracts import SemanticConcept
from src.shared.cognitive_planning_contracts import EvidencePackage
from src.brain_core.memory.interfaces import MemoryProvider, MemoryEntry

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

@pytest.fixture
def mock_memory():
    return AsyncMock(spec=MemoryProvider)

@pytest.mark.asyncio
async def test_case_outcome_saved_to_memory(mock_brain, mock_gateway, mock_knowledge, mock_memory):
    orchestrator = InventoryIntelligenceOrchestrator(
        brain_orchestrator=mock_brain, 
        gateway=mock_gateway, 
        knowledge=mock_knowledge,
        memory=mock_memory
    )
    
    mock_gateway.generate.side_effect = [
        # Intent Phase
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "requirement": {
                    "semantic_description": "urgent escalation",
                    "capability_urn": "urn:aarambooks:inventory:capability:balance",
                    "constraints": [],
                    "decision_criteria": "low stock means < 10"
                }
            }
            ```''',
            model_used="mock", prompt_tokens=10, completion_tokens=15
        ),
        # Reasoning Phase
        GatewayGenerationResponse(content="The evidence indicates a severe issue.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        # Action Phase
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1",
        plan_id="direct",
        sufficiency_assessment="SUFFICIENT",
        gaps=[],
        evidence_items=[]
    )
    
    await orchestrator.handle_query("Urgent stock exception", "user_123")
    
    # Assert memory write
    assert mock_memory.write_memory.call_count == 1
    entry = mock_memory.write_memory.call_args[0][0]
    assert isinstance(entry, MemoryEntry)
    assert entry.metadata["criteria_provenance"] == "USER_SUPPLIED"
    assert entry.metadata["decision_criteria"] == "low stock means < 10"
