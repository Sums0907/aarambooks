import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Optional

from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationResponse
from src.brain_core.planning.planner import CognitivePlanner
from src.brain_core.orchestration.resolver import CapabilityResolver
from src.brain_core.orchestration.orchestrator import BrainOrchestrator
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.context_engine.registry import ProviderRegistry, CapabilityMetadata
from src.brain_core.semantics.resolver import GenericSemanticResolver
from src.shared.context_contracts.provider import ContextRetrievalStatus, ContextCapabilityResult
from src.shared.semantic_resolution_contracts import DomainSemanticKnowledge, SemanticConcept, ResolvedSemanticRequirement, SemanticConstraint

from src.shared.cognitive_planning_contracts import (
    EvidenceRequirement,
    EvidencePlan,
    GapSemantics,
    ResolutionStatus,
    ProvenanceMetadata
)

@pytest.fixture
def mock_gateway():
    gateway = AsyncMock(spec=ModelGatewayProvider)
    return gateway

@pytest.fixture
def planner(mock_gateway):
    return CognitivePlanner(gateway=mock_gateway)

@pytest.fixture
def registry():
    from datetime import datetime, UTC
    reg = ProviderRegistry()
    mock_provider = AsyncMock()
    mock_provider.invoke_capability.return_value = ContextCapabilityResult(
        status=ContextRetrievalStatus.SUCCESS,
        data={"mock": "data"},
        provenance_metadata=ProvenanceMetadata(
            source_system="urn:aaram:source:mock",
            retrieval_timestamp=datetime.now(UTC),
            derivation_metadata="Mock"
        )
    )
    metadata = CapabilityMetadata(provides_identities={"mock_identity"}, supported_constraint_types={"mock_constraint"})
    reg.register("urn:aaram:capability:mock", metadata, mock_provider)
    return reg

@pytest.fixture
def resolver(registry):
    return CapabilityResolver(registry=registry)

@pytest.fixture
def assembler(registry):
    return ContextAssembler(registry=registry)

class DummySemanticKnowledge(DomainSemanticKnowledge):
    def get_concept(self, term: str) -> Optional[SemanticConcept]:
        return None
    def search_concepts(self, query: str) -> list[SemanticConcept]:
        return []

@pytest.fixture
def semantic_resolver():
    return GenericSemanticResolver(DummySemanticKnowledge())

@pytest.fixture
def orchestrator(planner, resolver, assembler, semantic_resolver):
    return BrainOrchestrator(planner=planner, resolver=resolver, assembler=assembler, semantic_resolver=semantic_resolver)

@pytest.mark.asyncio
async def test_planner_produces_evidence_plan(planner, mock_gateway):
    # Test 1 & 2: NL -> CognitivePlanner -> EvidencePlan
    # Mock LLM JSON output
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content='''```json
        {
            "original_intent": "find generic metrics",
            "requirements": [
                {
                    "requirement_id": "req-1",
                    "semantic_description": "generic metrics",
                    "necessity": "REQUIRED"
                }
            ]
        }
        ```''',
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=20
    )
    plan = await planner.propose_plan("Find me generic metrics")
    assert isinstance(plan, EvidencePlan)
    assert len(plan.requirements) == 1
    # Test 4 & 5: Planner does no physical retrieval, just returns plan

@pytest.mark.asyncio
async def test_planner_rejects_invalid_output(planner, mock_gateway):
    # Test 3: Invalid planner output
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content="invalid json {[[[",
        model_used="mock-model",
        prompt_tokens=10,
        completion_tokens=5
    )
    with pytest.raises(ValueError):
        await planner.propose_plan("Bad query")

def test_resolver_exact_match(resolver, semantic_resolver):
    # Test 6: CapabilityResolver resolves known capabilities
    req = EvidenceRequirement(
        requirement_id="req-1",
        semantic_description="test",
        rationale="test",
        necessity="REQUIRED"
    )
    resolved_req = semantic_resolver.resolve(req)
    resolved_req.core_identities = {"mock_identity"}
    resolved_req.semantic_gaps = []
    resolved_req.semantic_constraints = [
        SemanticConstraint(identity="cid", constraint_type="mock_constraint", operator="EQUALS")
    ]
    res = resolver.resolve(resolved_req)
    assert res.status == ResolutionStatus.EXACT_MATCH_CAPABILITY
    assert "urn:aaram:capability:mock" in res.resolved_capabilities

def test_resolver_unknown_capability(resolver, semantic_resolver):
    # Test 7: CapabilityResolver reports unknown correctly
    req = EvidenceRequirement(
        requirement_id="req-2",
        semantic_description="test",
        rationale="test",
        necessity="REQUIRED"
    )
    resolved_req = semantic_resolver.resolve(req)
    # Will not match because provides_identities doesn't match
    resolved_req.core_identities = {"unknown_identity"}
    resolved_req.semantic_gaps = []
    res = resolver.resolve(resolved_req)
    assert res.status == ResolutionStatus.DYNAMIC_DISCOVERY_REQUIRED

@pytest.mark.asyncio
async def test_orchestrator_coordinates_flow(orchestrator, mock_gateway):
    # Test 8, 9: Orchestrator coordinates flow, Package contains provenance
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content='''
        {
            "original_intent": "orchestrator test",
            "requirements": [
                {
                    "requirement_id": "req-1",
                    "semantic_description": "orchestrator test data",
                    "necessity": "REQUIRED"
                }
            ]
        }
        ''',
        model_used="mock",
        prompt_tokens=1,
        completion_tokens=1
    )
    
    # Force semantic resolver to output matching req so it succeeds
    old_resolve = orchestrator._semantic_resolver.resolve
    def mock_resolve(req):
        res = old_resolve(req)
        res.core_identities = {"mock_identity"}
        res.semantic_gaps = []
        res.semantic_constraints = [
            SemanticConstraint(identity="cid", constraint_type="mock_constraint", operator="EQUALS")
        ]
        return res
    orchestrator._semantic_resolver.resolve = mock_resolve
    
    package = await orchestrator.handle_query("orchestrator test", "user123")
    assert package.sufficiency_assessment == "SUFFICIENT"
    assert len(package.evidence_items) == 1
    item = package.evidence_items[0]
    assert item.provenance is not None
    assert item.provenance.source_system == "urn:aaram:source:mock"
    assert item.gap_semantics == GapSemantics.EVIDENCE_SUFFICIENT

@pytest.mark.asyncio
async def test_gap_semantics_distinguished(orchestrator, mock_gateway):
    # Test 10, 11, 12: Missing data, capability, and semantic gap distinguishable
    mock_gateway.generate.side_effect = [
        GatewayGenerationResponse(
            content='''
            {
                "original_intent": "gap test",
                "requirements": [
                    {
                        "requirement_id": "req-1",
                        "semantic_description": "no capability",
                        "necessity": "REQUIRED"
                    }
                ]
            }
            ''',
            model_used="mock", prompt_tokens=1, completion_tokens=1
        ),
        GatewayGenerationResponse(
            content='''
            {
                "reason_for_extension": "stop",
                "new_requirements": []
            }
            ''',
            model_used="mock", prompt_tokens=1, completion_tokens=1
        ),
        GatewayGenerationResponse(
            content='''
            {
                "original_intent": "gap test",
                "requirements": [
                    {
                        "requirement_id": "req-1",
                        "semantic_description": "no capability",
                        "necessity": "REQUIRED"
                    }
                ]
            }
            ''',
            model_used="mock", prompt_tokens=1, completion_tokens=1
        ),
        GatewayGenerationResponse(
            content='''
            {
                "reason_for_extension": "stop",
                "new_requirements": []
            }
            ''',
            model_used="mock", prompt_tokens=1, completion_tokens=1
        )
    ]
    
    old_resolve = orchestrator._semantic_resolver.resolve
    def mock_resolve_gap(req):
        res = old_resolve(req)
        res.core_identities = {"unknown_identity"}
        res.semantic_gaps = []
        return res
    orchestrator._semantic_resolver.resolve = mock_resolve_gap

    package = await orchestrator.handle_query("gap test", "user123")
    assert package.sufficiency_assessment == "INSUFFICIENT"
    assert package.evidence_items[0].gap_semantics == GapSemantics.CONTEXT_CAPABILITY_UNAVAILABLE

@pytest.mark.asyncio
async def test_iterative_planning_bounded(orchestrator, mock_gateway):
    # Test 13, 14: Evidence extension triggers, bounded execution
    mock_gateway.generate.return_value = GatewayGenerationResponse(
        content='''
        {
            "original_intent": "iterative loop",
            "requirements": [
                {
                    "requirement_id": "req-1",
                    "semantic_description": "loop",
                    "necessity": "REQUIRED"
                }
            ],
            "new_requirements": [
                {
                    "requirement_id": "req-1",
                    "semantic_description": "loop",
                    "necessity": "REQUIRED"
                }
            ]
        }
        ''',
        model_used="mock", prompt_tokens=1, completion_tokens=1
    )
    
    old_resolve = orchestrator._semantic_resolver.resolve
    def mock_resolve_gap2(req):
        res = old_resolve(req)
        res.core_identities = {"unknown_identity"}
        res.semantic_gaps = []
        return res
    orchestrator._semantic_resolver.resolve = mock_resolve_gap2
    
    package = await orchestrator.handle_query("loop query", "user123")
    assert orchestrator._max_iterations == 3
    # Call count should be 1 (plan) + 3 (extensions) = 4
    assert mock_gateway.generate.call_count == 4
    assert package.sufficiency_assessment == "INSUFFICIENT"

@pytest.mark.asyncio
async def test_direct_execution_boundary(orchestrator):
    # Test 15: Proves a generic EvidenceRequirement can be submitted through the new public interface.
    # We bypass handle_query() entirely.
    req = EvidenceRequirement(
        requirement_id="req-direct-1",
        semantic_description="direct boundary test",
        rationale="test",
        necessity="REQUIRED"
    )
    
    old_resolve = orchestrator._semantic_resolver.resolve
    def mock_resolve(req_obj):
        res = old_resolve(req_obj)
        res.core_identities = {"mock_identity"}
        res.semantic_gaps = []
        res.semantic_constraints = [
            SemanticConstraint(identity="cid", constraint_type="mock_constraint", operator="EQUALS")
        ]
        return res
    orchestrator._semantic_resolver.resolve = mock_resolve
    
    package = await orchestrator.execute_requirements([req], "test_user")
    
    assert package.sufficiency_assessment == "SUFFICIENT"
    assert len(package.evidence_items) == 1
    item = package.evidence_items[0]
    assert item.provenance is not None
    assert item.provenance.source_system == "urn:aaram:source:mock"
    assert item.gap_semantics == GapSemantics.EVIDENCE_SUFFICIENT
    assert package.plan_id == "direct-execution"
