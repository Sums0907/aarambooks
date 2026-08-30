import pytest
import asyncio
import httpx
from src.shared.config import settings
from src.infrastructure.adapters.httpx_client import HttpxClientAdapter
from src.infrastructure.gateway_config import ConfigDrivenGatewayConfiguration
from src.infrastructure.context_capability_gateway import ContextCapabilityGateway
from src.brain_core.context_engine.registry import ProviderRegistry, CapabilityMetadata
from src.brain_core.context_engine.assembler import ContextAssembler
from src.shared.cognitive_planning_contracts import (
    ContextAssemblyRequest, ResolutionStatus, CapabilityResolutionResult, EvidenceRequirement
)
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement, SemanticConstraint

async def get_real_token() -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.identity_url}/auth/service-token",
                json={
                    "client_id": settings.brain_client_id,
                    "client_secret": settings.brain_client_secret
                }
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
    except Exception as e:
        pytest.skip(f"Authentication BLOCKED - real M2M credentials unavailable: {e}")

@pytest.fixture
def live_assembler_setup():
    registry = ProviderRegistry()
    config = ConfigDrivenGatewayConfiguration(settings.capability_routes)
    http_client = HttpxClientAdapter()
    gateway = ContextCapabilityGateway(config, http_client)
    
    # Register the 4 capabilities
    capabilities = [
        "urn:aarambooks:inventory:capability:balance",
        "urn:aarambooks:inventory:capability:ledger",
        "urn:aarambooks:inventory:capability:jobwork_status",
        "urn:aarambooks:inventory:capability:exception_status"
    ]
    
    for cap in capabilities:
        registry.register(
            cap,
            CapabilityMetadata(provides_identities={"inventory.entity.sku"}, supported_constraint_types={"ENTITY"}),
            gateway
        )
        
    assembler = ContextAssembler(registry)
    return assembler

@pytest.mark.asyncio
async def test_live_balance_capability(live_assembler_setup):
    assembler = live_assembler_setup
    token = await get_real_token()
    
    req = ContextAssemblyRequest(
        request_id="live-req-1",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-1",
            original_requirement=EvidenceRequirement(
                requirement_id="req-1",
                semantic_description="balance check",
                semantic_intent="informational",
                rationale="E2E Certification"
            ),
            core_identities={"inventory.entity.sku", "inventory.entity.warehouse"},
            semantic_constraints=[
                SemanticConstraint(
                    identity="inventory.entity.sku",
                    constraint_type="ENTITY",
                    operator="EQUALS",
                    bound_value="SKU-123"
                ),
                SemanticConstraint(
                    identity="inventory.entity.warehouse",
                    constraint_type="ENTITY",
                    operator="EQUALS",
                    bound_value="WH-001"
                )
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context=f"Bearer {token}"
    )
    
    res = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aarambooks:inventory:capability:balance"]
    )
    
    evidence = await assembler.assemble_evidence(req, res)
    
    assert len(evidence) == 1
    ev = evidence[0]
    # In a real system, SKU-123 might not exist, leading to DATA_UNAVAILABLE or a SUCCESS with empty data.
    # But it should not raise an unhandled exception or contract error!
    assert ev.gap_semantics in ["EVIDENCE_SUFFICIENT", "DATA_UNAVAILABLE", "PROVIDER_EXECUTION_ERROR"]
    
    # Contract constraint checks
    if ev.gap_semantics == "EVIDENCE_SUFFICIENT":
        assert ev.provenance.source_system.startswith("urn:aaram:")
        assert ev.data_payload is not None

@pytest.mark.asyncio
async def test_live_ledger_capability(live_assembler_setup):
    assembler = live_assembler_setup
    token = await get_real_token()
    req = ContextAssemblyRequest(
        request_id="live-req-2",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-2",
            original_requirement=EvidenceRequirement(
                requirement_id="req-2",
                semantic_description="ledger check",
                semantic_intent="informational",
                rationale="E2E Certification"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[
                SemanticConstraint(identity="inventory.entity.sku", constraint_type="ENTITY", operator="EQUALS", bound_value="SKU-123")
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context=f"Bearer {token}"
    )
    res = CapabilityResolutionResult(
        requirement_id="req-2", status=ResolutionStatus.EXACT_MATCH_CAPABILITY, resolved_capabilities=["urn:aarambooks:inventory:capability:ledger"]
    )
    evidence = await assembler.assemble_evidence(req, res)
    assert len(evidence) == 1
    assert evidence[0].gap_semantics in ["EVIDENCE_SUFFICIENT", "DATA_UNAVAILABLE", "PROVIDER_EXECUTION_ERROR"]
    
@pytest.mark.asyncio
async def test_live_jobwork_capability(live_assembler_setup):
    assembler = live_assembler_setup
    token = await get_real_token()
    req = ContextAssemblyRequest(
        request_id="live-req-3",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-3",
            original_requirement=EvidenceRequirement(
                requirement_id="req-3", semantic_description="jobwork check", semantic_intent="informational", rationale="test"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[
                SemanticConstraint(identity="inventory.entity.sku", constraint_type="ENTITY", operator="EQUALS", bound_value="SKU-123")
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context=f"Bearer {token}"
    )
    res = CapabilityResolutionResult(requirement_id="req-3", status=ResolutionStatus.EXACT_MATCH_CAPABILITY, resolved_capabilities=["urn:aarambooks:inventory:capability:jobwork_status"])
    evidence = await assembler.assemble_evidence(req, res)
    assert len(evidence) == 1
    assert evidence[0].gap_semantics in ["EVIDENCE_SUFFICIENT", "DATA_UNAVAILABLE", "PROVIDER_EXECUTION_ERROR"]

@pytest.mark.asyncio
async def test_live_exception_capability(live_assembler_setup):
    assembler = live_assembler_setup
    token = await get_real_token()
    req = ContextAssemblyRequest(
        request_id="live-req-4",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-4",
            original_requirement=EvidenceRequirement(
                requirement_id="req-4", semantic_description="exception check", semantic_intent="informational", rationale="test"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[
                SemanticConstraint(identity="inventory.entity.sku", constraint_type="ENTITY", operator="EQUALS", bound_value="SKU-123")
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context=f"Bearer {token}"
    )
    res = CapabilityResolutionResult(requirement_id="req-4", status=ResolutionStatus.EXACT_MATCH_CAPABILITY, resolved_capabilities=["urn:aarambooks:inventory:capability:exception_status"])
    evidence = await assembler.assemble_evidence(req, res)
    assert len(evidence) == 1
    assert evidence[0].gap_semantics in ["EVIDENCE_SUFFICIENT", "DATA_UNAVAILABLE", "PROVIDER_EXECUTION_ERROR"]
