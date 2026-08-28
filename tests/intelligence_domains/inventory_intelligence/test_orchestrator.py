import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.intelligence_domains.inventory_intelligence.knowledge import InventorySemanticKnowledge
from src.brain_core.orchestration.orchestrator import BrainOrchestrator
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationResponse
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, GapSemantics, ProvenanceMetadata
from src.shared.semantic_resolution_contracts import SemanticConcept

from datetime import datetime, UTC

@pytest.fixture
def mock_gateway():
    return AsyncMock(spec=ModelGatewayProvider)

@pytest.fixture
def mock_brain():
    return AsyncMock(spec=BrainOrchestrator)

@pytest.fixture
def mock_knowledge():
    k = MagicMock(spec=InventorySemanticKnowledge)
    k.get_certified_capabilities.return_value = [
        SemanticConcept(
            concept_id="inventory.capability.balance", 
            concept_name="Balance Capability", 
            concept_type="CAPABILITY", 
            aliases=[], 
            metadata={
                "urn": "urn:aarambooks:inventory:capability:balance",
                "required_constraints": ["inventory.entity.sku", "inventory.entity.warehouse"],
                "optional_constraints": []
            }
        ),
        SemanticConcept(
            concept_id="inventory.capability.ledger",
            concept_name="Ledger Capability",
            concept_type="CAPABILITY",
            aliases=[],
            metadata={
                "urn": "urn:aarambooks:inventory:capability:ledger",
                "required_constraints": ["inventory.entity.sku"],
                "optional_constraints": ["inventory.temporal.posting_date"]
            }
        ),
        SemanticConcept(
            concept_id="inventory.capability.jobwork_status",
            concept_name="Jobwork Status",
            concept_type="CAPABILITY",
            aliases=[],
            metadata={
                "urn": "urn:aarambooks:inventory:capability:jobwork_status",
                "required_constraints": ["inventory.entity.jobwork_vendor"],
                "optional_constraints": ["inventory.entity.sku"]
            }
        ),
        SemanticConcept(
            concept_id="inventory.capability.exception_status",
            concept_name="Exception Status",
            concept_type="CAPABILITY",
            aliases=[],
            metadata={
                "urn": "urn:aarambooks:inventory:capability:exception_status",
                "required_constraints": ["inventory.entity.sku"],
                "optional_constraints": ["inventory.temporal.exception_date"]
            }
        )
    ]
    k.get_unsupported_policies.return_value = [
        SemanticConcept(concept_id="urn:low_stock", concept_name="Low Stock", concept_type="POLICY", aliases=[], description="low stock")
    ]
    return k

@pytest.mark.asyncio
async def test_balance_query_produces_explicit_constraints(mock_brain, mock_gateway, mock_knowledge):
    """A. Balance query produces explicit SKU and Warehouse constraint."""
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "requirement": {
                    "semantic_description": "balance for SKU X in WH1",
                    "capability_urn": "urn:aarambooks:inventory:capability:balance",
                    "constraints": [
                        {"identity": "inventory.entity.sku", "bound_value": "SKU X"},
                        {"identity": "inventory.entity.warehouse", "bound_value": "WH1"}
                    ]
                }
            }
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        ),
        GatewayGenerationResponse(content="The current stock level is 100 units.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1", plan_id="direct", sufficiency_assessment="SUFFICIENT", gaps=[],
        evidence_items=[EvidenceItem(item_id="item-1", semantic_identity="stock", data_payload={"stock": 100}, provenance=ProvenanceMetadata(retrieval_timestamp=datetime.now(UTC)), gap_semantics=GapSemantics.EVIDENCE_SUFFICIENT)]
    )
    
    answer = await orchestrator.handle_query("What is the stock of item X in WH1?", "user_123")
    
    reqs = mock_brain.execute_requirements.call_args[0][0]
    assert len(reqs) == 1
    resolved_req = reqs[0]
    # G. Structured requirements reach Brain Core
    assert hasattr(resolved_req, "semantic_constraints")
    
    identities = [c.identity for c in resolved_req.semantic_constraints]
    assert "inventory.capability.balance" in identities
    assert "inventory.entity.sku" in identities
    assert "inventory.entity.warehouse" in identities

@pytest.mark.asyncio
async def test_missing_required_constraint_produces_gap(mock_brain, mock_gateway, mock_knowledge):
    """E. Missing required constraints are NOT invented."""
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    # Missing warehouse constraint
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content='''```json
        {
            "status": "SUPPORTED",
            "requirement": {
                "semantic_description": "balance for SKU X",
                "capability_urn": "urn:aarambooks:inventory:capability:balance",
                "constraints": [
                    {"identity": "inventory.entity.sku", "bound_value": "SKU X"}
                ]
            }
        }
        ```''',
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=15
    )
    
    answer = await orchestrator.handle_query("What is the stock of item X?", "user_123")
    
    assert "Clarification needed: Missing required constraints" in answer
    assert "inventory.entity.warehouse" in answer
    mock_brain.execute_requirements.assert_not_called()

@pytest.mark.asyncio
async def test_rejects_unsupported_query(mock_brain, mock_gateway, mock_knowledge):
    """F. Unsupported concepts remain rejected."""
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content='''```json
        {
            "status": "UNSUPPORTED",
            "reason": "We do not track low stock."
        }
        ```''',
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=15
    )
    
    answer = await orchestrator.handle_query("Which items have low stock?", "user_123")
    
    assert "Unsupported: We do not track low stock." in answer
    mock_brain.execute_requirements.assert_not_called()

@pytest.mark.asyncio
async def test_ledger_query_produces_explicit_constraints(mock_brain, mock_gateway, mock_knowledge):
    """B. Ledger query produces explicit SKU and optional posting_date constraint."""
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "requirement": {
                    "semantic_description": "ledger for SKU X",
                    "capability_urn": "urn:aarambooks:inventory:capability:ledger",
                    "constraints": [
                        {"identity": "inventory.entity.sku", "bound_value": "SKU X"},
                        {"identity": "inventory.temporal.posting_date", "bound_value": "today"}
                    ]
                }
            }
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        ),
        GatewayGenerationResponse(content="The ledger shows 5 in, 2 out.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1", plan_id="direct", sufficiency_assessment="SUFFICIENT", gaps=[],
        evidence_items=[]
    )
    
    answer = await orchestrator.handle_query("What is the history of item X today?", "user_123")
    
    reqs = mock_brain.execute_requirements.call_args[0][0]
    identities = [c.identity for c in reqs[0].semantic_constraints]
    assert "inventory.capability.ledger" in identities
    assert "inventory.entity.sku" in identities
    assert "inventory.temporal.posting_date" in identities

@pytest.mark.asyncio
async def test_jobwork_query_produces_explicit_constraints(mock_brain, mock_gateway, mock_knowledge):
    """C. Jobwork query produces explicit vendor constraint."""
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "requirement": {
                    "semantic_description": "jobwork status for vendor V1",
                    "capability_urn": "urn:aarambooks:inventory:capability:jobwork_status",
                    "constraints": [
                        {"identity": "inventory.entity.jobwork_vendor", "bound_value": "V1"}
                    ]
                }
            }
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        ),
        GatewayGenerationResponse(content="Vendor V1 has 10 units.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1", plan_id="direct", sufficiency_assessment="SUFFICIENT", gaps=[],
        evidence_items=[]
    )
    
    answer = await orchestrator.handle_query("What is pending with V1?", "user_123")
    
    reqs = mock_brain.execute_requirements.call_args[0][0]
    identities = [c.identity for c in reqs[0].semantic_constraints]
    assert "inventory.capability.jobwork_status" in identities
    assert "inventory.entity.jobwork_vendor" in identities

@pytest.mark.asyncio
async def test_exception_query_produces_explicit_constraints(mock_brain, mock_gateway, mock_knowledge):
    """D. Exception query produces explicit SKU constraint."""
    orchestrator = InventoryIntelligenceOrchestrator(brain_orchestrator=mock_brain, gateway=mock_gateway, knowledge=mock_knowledge)
    
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''```json
            {
                "status": "SUPPORTED",
                "requirement": {
                    "semantic_description": "exceptions for SKU X",
                    "capability_urn": "urn:aarambooks:inventory:capability:exception_status",
                    "constraints": [
                        {"identity": "inventory.entity.sku", "bound_value": "SKU X"}
                    ]
                }
            }
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        ),
        GatewayGenerationResponse(content="SKU X has 2 discrepancies.", model_used="mock", prompt_tokens=10, completion_tokens=15),
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]

    mock_brain.execute_requirements.return_value = EvidencePackage(
        package_id="pkg-1", plan_id="direct", sufficiency_assessment="SUFFICIENT", gaps=[],
        evidence_items=[]
    )
    
    answer = await orchestrator.handle_query("Any mismatch for SKU X?", "user_123")
    
    reqs = mock_brain.execute_requirements.call_args[0][0]
    identities = [c.identity for c in reqs[0].semantic_constraints]
    assert "inventory.capability.exception_status" in identities
    assert "inventory.entity.sku" in identities
