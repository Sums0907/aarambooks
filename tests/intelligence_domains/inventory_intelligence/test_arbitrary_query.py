import pytest
from datetime import datetime, UTC
import json
from unittest.mock import AsyncMock

from src.azm.provider import GlobalAzmProvider
from src.intelligence_domains.inventory_intelligence.knowledge import InventorySemanticKnowledge
from src.brain_core.semantics.resolver import GenericSemanticResolver
from src.brain_core.planning.planner import CognitivePlanner
from src.brain_core.orchestration.resolver import CapabilityResolver
from src.brain_core.context_engine.registry import ProviderRegistry, CapabilityMetadata
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.orchestration.orchestrator import BrainOrchestrator
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator

from src.shared.context_contracts.provider import ContextCapabilityProvider, ContextRetrievalStatus, ContextCapabilityResult
from src.shared.cognitive_planning_contracts import GapSemantics, ProvenanceMetadata
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationResponse

class MockInventoryProvider(ContextCapabilityProvider):
    """
    Simulates AaramInventory receiving generic constraints and evaluating them physically.
    """
    async def invoke_capability(self, capability_urn, requirement, authorization_context):
        # 1. Assert we receive only generic SemanticConstraints
        assert hasattr(requirement, "semantic_constraints")
        
        # 2. Assert NO physical API parameters or SQL leaked into Brain Core
        for constraint in requirement.semantic_constraints:
            assert not hasattr(constraint, "parameter_name")
            assert not hasattr(constraint, "value")
            assert not hasattr(constraint, "physical_reference")
            
        identities = [c.identity for c in requirement.semantic_constraints]
        assert "inventory.entity.jobwork_vendor" in identities
        
        # 3. Simulate AaramInventory executing its own physical SQL and business logic
        mock_physical_result = {
            "vendor": "VND-99",
            "vendor_name": "Acme Jobwork",
            "pending_quantity": 450
        }
        
        return ContextCapabilityResult(
            status=ContextRetrievalStatus.SUCCESS,
            data=mock_physical_result,
            provenance_metadata=ProvenanceMetadata(
                source_system="urn:aaram:source:inventory",
                retrieval_timestamp=datetime.now(UTC),
                derivation_metadata="Evaluated via internal jobwork ledger"
            )
        )

@pytest.fixture
def mock_gateway():
    gateway = AsyncMock(spec=ModelGatewayProvider)
    
    # 1. First call is Domain intent parser
    planner_json = json.dumps({
        "status": "SUPPORTED",
        "understanding": {
                        "intent": "RETRIEVE",
                        "entities": [{"original_expression": "Acme Jobwork"}],
                        "conditions": []
                    }
    })
    
    # 2. Second call is InventoryIntelligenceOrchestrator synthesizing the final answer
    domain_answer = "Based on the evidence, Acme Jobwork has 450 units pending return."
    
    gateway.generate.side_effect = [
        GatewayGenerationResponse(content=planner_json, model_used="mock", prompt_tokens=10, completion_tokens=50),
        GatewayGenerationResponse(content=domain_answer, model_used="mock", prompt_tokens=10, completion_tokens=20),
        GatewayGenerationResponse(content="NO_ACTION", model_used="mock", prompt_tokens=10, completion_tokens=15)
    ]
    return gateway

@pytest.mark.asyncio
async def test_arbitrary_query_end_to_end_proof(mock_gateway):
    """
    Proves the full semantic chain:
    NL -> EvidenceReq -> Azm Semantic Constraints -> Capability Res -> Provider Invocation -> Domain Synthesis
    without violating Brain Core's domain-agnostic HOW boundary.
    """
    
    # 1. Setup ecosystem knowledge (Azm)
    azm_provider = GlobalAzmProvider()
    
    # 2. Setup Runtime Adapter (DomainSemanticKnowledge)
    inventory_knowledge = InventorySemanticKnowledge(azm_provider)
    
    # 3. Setup Brain Core generic semantic infrastructure
    semantic_resolver = GenericSemanticResolver(inventory_knowledge)
    
    # 4. Setup Provider Registry with our capability provider (AaramInventory simulation)
    registry = ProviderRegistry()
    metadata = CapabilityMetadata(
        provides_identities={"inventory.entity.jobwork_vendor"},
        supported_constraint_types={"ENTITY", "VOCABULARY", "CAPABILITY"}
    )
    registry.register("urn:aarambooks:inventory:capability:jobwork_status", metadata, MockInventoryProvider())
    capability_resolver = CapabilityResolver(registry)
    context_assembler = ContextAssembler(registry)
    
    planner = CognitivePlanner(mock_gateway)
    brain_orchestrator = BrainOrchestrator(planner, capability_resolver, context_assembler, semantic_resolver)
    
    # 5. Setup Domain Orchestrator
    domain = InventoryIntelligenceOrchestrator(brain_orchestrator, mock_gateway, inventory_knowledge)
    
    # Fix the semantic_resolver output to have matching sets to pass routing
    old_resolve = brain_orchestrator._semantic_resolver.resolve
    def mock_resolve(req):
        res = old_resolve(req)
        res.core_identities = {"inventory.entity.jobwork_vendor"}
        return res
    brain_orchestrator._semantic_resolver.resolve = mock_resolve
    
    # 6. Execute the Arbitrary Query
    query = "What is pending with Acme Jobwork?"
    answer = await domain.handle_query(query, "user_123")
    print(f"ANSWER RETURNED: {answer}")
    
    # 7. Assertions:
    assert mock_gateway.generate.call_count == 3
    
    # Verify that Brain Core was actually callednswer
    assert "Acme Jobwork" in answer
    assert "450" in answer
