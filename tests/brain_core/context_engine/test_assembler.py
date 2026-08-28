import pytest
from datetime import datetime, UTC
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.context_engine.registry import ProviderRegistry, ProviderNotRegisteredError, CapabilityMetadata
from src.shared.context_contracts.source import ContextSourceURN, ContextSource
from src.shared.context_contracts.capability import CapabilityURN
from src.shared.context_contracts.provider import ContextCapabilityProvider, ContextRetrievalStatus, ContextCapabilityResult
from src.shared.cognitive_planning_contracts import (
    ContextAssemblyRequest as EvContextAssemblyRequest,
    CapabilityResolutionResult,
    ResolutionStatus,
    EvidenceRequirement,
    GapSemantics,
    ProvenanceMetadata
)
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement

class MockPhysicalProvider(ContextCapabilityProvider):
    def __init__(self, status: ContextRetrievalStatus, data=None):
        self.status = status
        self.data = data
        
    async def invoke_capability(self, capability_urn, requirement, authorization_context):
        return ContextCapabilityResult(
            status=self.status,
            data=self.data,
            provenance_metadata=ProvenanceMetadata(
                source_system="urn:aaram:source:inventory",
                retrieval_timestamp=datetime.now(UTC),
                derivation_metadata="Mock Provider"
            )
        )

@pytest.fixture
def base_evidence_req():
    req = EvidenceRequirement(requirement_id="req-1", semantic_description="Test", necessity="REQUIRED", rationale="Test")
    return ResolvedSemanticRequirement(
        requirement_id="req-1",
        original_requirement=req
    )

@pytest.mark.asyncio
async def test_assemble_evidence_success(base_evidence_req):
    reg = ProviderRegistry()
    md = CapabilityMetadata(provides_identities={"inv"}, supported_constraint_types=set())
    reg.register("urn:aaram:capability:inventory", md, MockPhysicalProvider(ContextRetrievalStatus.SUCCESS, data={"stock": 10}))
    assembler = ContextAssembler(reg)
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aaram:capability:inventory"]
    )
    
    req = EvContextAssemblyRequest(
        request_id="assembly-1",
        resolved_requirement=base_evidence_req,
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="user_123"
    )
    
    evidence_list = await assembler.assemble_evidence(req, res)
    assert len(evidence_list) == 1
    evidence = evidence_list[0]
    assert evidence.gap_semantics == GapSemantics.EVIDENCE_SUFFICIENT
    assert evidence.data_payload == {"stock": 10}
    assert evidence.provenance.source_system == "urn:aaram:source:inventory"

@pytest.mark.asyncio
async def test_assemble_evidence_data_unavailable(base_evidence_req):
    reg = ProviderRegistry()
    md = CapabilityMetadata(provides_identities={"inv"}, supported_constraint_types=set())
    reg.register("urn:aaram:capability:inventory", md, MockPhysicalProvider(ContextRetrievalStatus.DATA_UNAVAILABLE))
    assembler = ContextAssembler(reg)
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aaram:capability:inventory"]
    )
    req = EvContextAssemblyRequest(
        request_id="assembly-2",
        resolved_requirement=base_evidence_req,
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="user_123"
    )
    
    evidence_list = await assembler.assemble_evidence(req, res)
    assert len(evidence_list) == 1
    evidence = evidence_list[0]
    assert evidence.gap_semantics == GapSemantics.DATA_UNAVAILABLE
    assert evidence.data_payload is None

@pytest.mark.asyncio
async def test_assemble_evidence_unauthorized(base_evidence_req):
    reg = ProviderRegistry()
    md = CapabilityMetadata(provides_identities={"inv"}, supported_constraint_types=set())
    reg.register("urn:aaram:capability:inventory", md, MockPhysicalProvider(ContextRetrievalStatus.UNAUTHORIZED))
    assembler = ContextAssembler(reg)
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aaram:capability:inventory"]
    )
    req = EvContextAssemblyRequest(
        request_id="assembly-3",
        resolved_requirement=base_evidence_req,
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="user_123"
    )
    
    evidence_list = await assembler.assemble_evidence(req, res)
    assert len(evidence_list) == 1
    evidence = evidence_list[0]
    assert evidence.gap_semantics == GapSemantics.DATA_INACCESSIBLE

@pytest.mark.asyncio
async def test_assemble_evidence_provider_not_registered(base_evidence_req):
    reg = ProviderRegistry()
    assembler = ContextAssembler(reg)
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aaram:capability:inventory"]
    )
    req = EvContextAssemblyRequest(
        request_id="assembly-4",
        resolved_requirement=base_evidence_req,
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="user_123"
    )
    
    evidence_list = await assembler.assemble_evidence(req, res)
    assert len(evidence_list) == 1
    evidence = evidence_list[0]
    assert evidence.gap_semantics == GapSemantics.CONTEXT_CAPABILITY_UNAVAILABLE

@pytest.mark.asyncio
async def test_assemble_evidence_error_maps_to_execution_error(base_evidence_req):
    reg = ProviderRegistry()
    md = CapabilityMetadata(provides_identities={"inv"}, supported_constraint_types=set())
    reg.register("urn:aaram:capability:inventory", md, MockPhysicalProvider(ContextRetrievalStatus.ERROR))
    assembler = ContextAssembler(reg)
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aaram:capability:inventory"]
    )
    req = EvContextAssemblyRequest(
        request_id="assembly-5",
        resolved_requirement=base_evidence_req,
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="user_123"
    )
    
    evidence_list = await assembler.assemble_evidence(req, res)
    assert len(evidence_list) == 1
    evidence = evidence_list[0]
    assert evidence.gap_semantics == GapSemantics.PROVIDER_EXECUTION_ERROR
    assert evidence.data_payload is None

@pytest.mark.asyncio
async def test_assemble_evidence_success_with_no_data_maps_to_unavailable(base_evidence_req):
    reg = ProviderRegistry()
    md = CapabilityMetadata(provides_identities={"inv"}, supported_constraint_types=set())
    reg.register("urn:aaram:capability:inventory", md, MockPhysicalProvider(ContextRetrievalStatus.SUCCESS, data=None))
    assembler = ContextAssembler(reg)
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aaram:capability:inventory"]
    )
    req = EvContextAssemblyRequest(
        request_id="assembly-6",
        resolved_requirement=base_evidence_req,
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="user_123"
    )
    
    evidence_list = await assembler.assemble_evidence(req, res)
    assert len(evidence_list) == 1
    evidence = evidence_list[0]
    assert evidence.gap_semantics == GapSemantics.DATA_UNAVAILABLE
