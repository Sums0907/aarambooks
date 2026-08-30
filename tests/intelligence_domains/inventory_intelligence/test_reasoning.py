import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata, GapSemantics
from src.brain_core.gateway.interfaces import GatewayGenerationResponse
from src.shared.semantic_resolution_contracts import SemanticConcept

@pytest.fixture
def mock_brain():
    brain = AsyncMock()
    return brain

@pytest.fixture
def mock_gateway():
    gateway = AsyncMock()
    return gateway

@pytest.fixture
def mock_knowledge():
    k = MagicMock()
    
    # Setup for IID-2 Intent Parse bypass
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
    
    # Setup for IID-3 Reasoning
    k.get_certified_policies.return_value = [
        SemanticConcept(
            concept_id="inventory.policy.immutable_movement",
            concept_name="Movement Immutability",
            concept_type="POLICY",
            aliases=[],
            description="Ledger movements are immutable once posted."
        )
    ]
    return k

@pytest.mark.asyncio
async def test_reasoning_injects_policies_and_handles_partial(mock_brain, mock_gateway, mock_knowledge):
    """
    Proves IID-3 reasoning handles PARTIAL sufficiency and injects certified policies.
    """
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        # 1. Intent Phase
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
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        ),
        # 2. Reasoning Phase
        GatewayGenerationResponse(content="The evidence shows 10 units, but note it is partial.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        # 3. Action Phase
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1",
        plan_id="direct",
        sufficiency_assessment="PARTIAL",
        gaps=[],
        evidence_items=[
            EvidenceItem(
                item_id="ev-1",
                semantic_identity="inventory.entity.sku",
                data_payload={"stock": 10},
                provenance=ProvenanceMetadata(
                    source_system="urn:aaram:inventory",
                    retrieval_timestamp=datetime.now(UTC),
                    derivation_metadata=""
                ),
                confidence_quality="0.9"
            )
        ]
    )
    
    answer = await orchestrator.handle_query("What is stock?", "user_123")
    
    # Assert output
    assert "10 units" in answer
    
    # Assert Reasoning Prompt contains Policy and Partial Note
    reasoning_req = mock_gateway.generate.call_args_list[1][0][0]
    system_prompt = reasoning_req.messages[0].content
    user_prompt = reasoning_req.messages[1].content
    
    assert "Movement Immutability" in system_prompt
    assert "NOTE: The evidence is PARTIAL" in system_prompt
    
    assert "Confidence: 0.9" in user_prompt
    assert "urn:aaram:inventory" in user_prompt

@pytest.mark.asyncio
async def test_reasoning_handles_insufficient_deterministically(mock_brain, mock_gateway, mock_knowledge):
    """
    Proves IID-3 halts and returns gap message deterministically on INSUFFICIENT evidence.
    """
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        # 1. Intent Phase
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
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        )
    ]
    
    # Notice we don't supply a 2nd Gateway response. If it calls the gateway again, it will throw StopIteration (which fails the test)

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1",
        plan_id="direct",
        sufficiency_assessment="INSUFFICIENT",
        gaps=[],
        evidence_items=[]
    )
    
    answer = await orchestrator.handle_query("What is stock?", "user_123")
    
    # Assert output is deterministic fallback
    assert "I cannot fully answer this question because required business data is unavailable" in answer
    assert mock_gateway.generate.call_count == 1
