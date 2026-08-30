from pydantic import ValidationError
import pytest
import asyncio
from datetime import datetime, UTC
from src.shared.context_contracts.provider import ContextRetrievalStatus, ContextCapabilityResult
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement, SemanticConstraint
from src.shared.cognitive_planning_contracts import EvidenceRequirement, ContextAssemblyRequest, CapabilityResolutionResult, ResolutionStatus
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.context_engine.registry import ProviderRegistry, CapabilityMetadata
from src.infrastructure.context_capability_gateway import ContextCapabilityGateway, HttpResponse
from src.infrastructure.gateway_config import ConfigDrivenGatewayConfiguration

# We mock HttpClient to act as the "network" boundary.
# This proves Brain emits generic payloads and expects generic responses.
class MockHttpClient:
    def __init__(self, responses=None):
        self.requests = []
        self.responses = responses or []

    async def post(self, url: str, headers: dict, json_payload: dict) -> HttpResponse:
        self.requests.append({"url": url, "headers": headers, "json_payload": json_payload})
        if self.responses:
            return self.responses.pop(0)
        return HttpResponse(status_code=500, error_message="No mock response")

@pytest.fixture
def assembler_setup():
    registry = ProviderRegistry()
    config = ConfigDrivenGatewayConfiguration({
        "urn:aarambooks:inventory:capability:balance": "http://mock-inventory-cem/api/v1/context/resolve",
        "urn:aarambooks:inventory:capability:ledger": "http://mock-inventory-cem/api/v1/context/resolve",
        "urn:aarambooks:inventory:capability:jobwork_status": "http://mock-inventory-cem/api/v1/context/resolve",
        "urn:aarambooks:inventory:capability:exception_status": "http://mock-inventory-cem/api/v1/context/resolve"
    })
    http_client = MockHttpClient()
    gateway = ContextCapabilityGateway(config, http_client)
    
    capabilities = [
        "urn:aarambooks:inventory:capability:balance",
        "urn:aarambooks:inventory:capability:ledger",
        "urn:aarambooks:inventory:capability:jobwork_status",
        "urn:aarambooks:inventory:capability:exception_status"
    ]
    for cap in capabilities:
        registry.register(
            cap,
            CapabilityMetadata(provides_identities={"inventory.entity.sku", "inventory.entity.jobwork_vendor"}, supported_constraint_types={"ENTITY"}),
            gateway
        )
    
    assembler = ContextAssembler(registry)
    return assembler, http_client

@pytest.mark.asyncio
async def test_cem_integration_success(assembler_setup):
    assembler, http_client = assembler_setup
    
    # Mocking compliant CEM response with provenance_metadata
    http_client.responses.append(HttpResponse(
        status_code=200,
        json_data={
            "status": "SUCCESS",
            "data": {"balance": 150},
            "provenance_metadata": {
                "source_system": "urn:aaram:source:inventory",
                "retrieval_timestamp": "2026-08-29T10:00:00Z"
            }
        }
    ))
    
    req = ContextAssemblyRequest(
        request_id="req-1",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-1",
            original_requirement=EvidenceRequirement(
                requirement_id="req-1",
                semantic_description="balance check",
                rationale="test"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[
                SemanticConstraint(
                    identity="inventory.entity.sku",
                    constraint_type="ENTITY",
                    operator="EQUALS",
                    bound_value="123"
                )
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="Bearer valid_token"
    )
    
    resolution = CapabilityResolutionResult(
        requirement_id="req-1",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aarambooks:inventory:capability:balance"]
    )
    
    evidence = await assembler.assemble_evidence(req, resolution)
    
    # 1. Assert Evidence output
    assert len(evidence) == 1
    assert evidence[0].gap_semantics == "EVIDENCE_SUFFICIENT"
    assert evidence[0].data_payload == {"balance": 150}
    assert evidence[0].provenance.source_system == "urn:aaram:source:inventory"
    
    # 2. Assert Transport request payload and headers
    assert len(http_client.requests) == 1
    request_made = http_client.requests[0]
    
    assert request_made["url"] == "http://mock-inventory-cem/api/v1/context/resolve"
    assert request_made["headers"]["Authorization"] == "Bearer valid_token"
    assert request_made["json_payload"]["capability_urn"] == "urn:aarambooks:inventory:capability:balance"
    assert request_made["json_payload"]["requirement"]["semantic_constraints"][0]["bound_value"] == "123"

@pytest.mark.asyncio
async def test_cem_integration_contract_mismatch(assembler_setup):
    assembler, http_client = assembler_setup
    
    # Mocking NON-COMPLIANT CEM response with `provenance` instead of `provenance_metadata`
    http_client.responses.append(HttpResponse(
        status_code=200,
        json_data={
            "status": "SUCCESS",
            "data": {"balance": 150},
            "provenance": { # THIS IS A VIOLATION
                "source_system": "urn:aaram:source:inventory",
                "retrieval_timestamp": "2026-08-29T10:00:00Z"
            }
        }
    ))
    
    req = ContextAssemblyRequest(
        request_id="req-2",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-2",
            original_requirement=EvidenceRequirement(
                requirement_id="req-2",
                semantic_description="balance check",
                rationale="test"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="Bearer valid_token"
    )
    
    resolution = CapabilityResolutionResult(
        requirement_id="req-2",
        status=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        resolved_capabilities=["urn:aarambooks:inventory:capability:balance"]
    )
    
    with pytest.raises(ValidationError) as exc_info:
        evidence = await assembler.assemble_evidence(req, resolution)
    
    assert "provenance" in str(exc_info.value)
    assert "Input should be a valid dictionary or instance of ProvenanceMetadata" in str(exc_info.value)

@pytest.mark.asyncio
async def test_cem_integration_ledger_capability(assembler_setup):
    assembler, http_client = assembler_setup
    http_client.responses.append(HttpResponse(
        status_code=200,
        json_data={
            "status": "SUCCESS",
            "data": {"movements": [{"date": "2026-01-01", "qty": 10}]},
            "provenance_metadata": {
                "source_system": "urn:aaram:source:inventory",
                "retrieval_timestamp": "2026-08-29T10:00:00Z"
            }
        }
    ))
    req = ContextAssemblyRequest(
        request_id="req-ledger",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-ledger",
            original_requirement=EvidenceRequirement(
                requirement_id="req-ledger",
                semantic_description="Show stock movements for SKU X between DATE_A and DATE_B.",
                rationale="Validation harness"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[
                SemanticConstraint(identity="inventory.entity.sku", constraint_type="ENTITY", operator="EQUALS", bound_value="SKU-123")
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="Bearer valid_token"
    )
    resolution = CapabilityResolutionResult(requirement_id="req-ledger", status=ResolutionStatus.EXACT_MATCH_CAPABILITY, resolved_capabilities=["urn:aarambooks:inventory:capability:ledger"])
    evidence = await assembler.assemble_evidence(req, resolution)
    
    assert len(evidence) == 1
    assert evidence[0].gap_semantics == "EVIDENCE_SUFFICIENT"
    assert "movements" in evidence[0].data_payload
    
    request_made = http_client.requests[-1]
    assert request_made["json_payload"]["capability_urn"] == "urn:aarambooks:inventory:capability:ledger"

@pytest.mark.asyncio
async def test_cem_integration_jobwork_capability(assembler_setup):
    assembler, http_client = assembler_setup
    http_client.responses.append(HttpResponse(
        status_code=200,
        json_data={
            "status": "SUCCESS",
            "data": {"pending_qty": 50},
            "provenance_metadata": {
                "source_system": "urn:aaram:source:inventory",
                "retrieval_timestamp": "2026-08-29T10:00:00Z"
            }
        }
    ))
    req = ContextAssemblyRequest(
        request_id="req-jobwork",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-jobwork",
            original_requirement=EvidenceRequirement(
                requirement_id="req-jobwork",
                semantic_description="What stock is currently pending with vendor V for SKU X?",
                rationale="Validation harness"
            ),
            core_identities={"inventory.entity.sku", "inventory.entity.jobwork_vendor"},
            semantic_constraints=[
                SemanticConstraint(identity="inventory.entity.sku", constraint_type="ENTITY", operator="EQUALS", bound_value="SKU-123"),
                SemanticConstraint(identity="inventory.entity.jobwork_vendor", constraint_type="ENTITY", operator="EQUALS", bound_value="VENDOR-A")
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="Bearer valid_token"
    )
    resolution = CapabilityResolutionResult(requirement_id="req-jobwork", status=ResolutionStatus.EXACT_MATCH_CAPABILITY, resolved_capabilities=["urn:aarambooks:inventory:capability:jobwork_status"])
    evidence = await assembler.assemble_evidence(req, resolution)
    
    assert len(evidence) == 1
    assert evidence[0].gap_semantics == "EVIDENCE_SUFFICIENT"
    assert evidence[0].data_payload["pending_qty"] == 50
    assert evidence[0].provenance.source_system == "urn:aaram:source:inventory"
    
    request_made = http_client.requests[-1]
    assert request_made["json_payload"]["capability_urn"] == "urn:aarambooks:inventory:capability:jobwork_status"

@pytest.mark.asyncio
async def test_cem_integration_exception_capability(assembler_setup):
    assembler, http_client = assembler_setup
    http_client.responses.append(HttpResponse(
        status_code=200,
        json_data={
            "status": "SUCCESS",
            "data": {"open_exceptions": 2},
            "provenance_metadata": {
                "source_system": "urn:aaram:source:inventory",
                "retrieval_timestamp": "2026-08-29T10:00:00Z"
            }
        }
    ))
    req = ContextAssemblyRequest(
        request_id="req-exception",
        resolved_requirement=ResolvedSemanticRequirement(
            requirement_id="req-exception",
            original_requirement=EvidenceRequirement(
                requirement_id="req-exception",
                semantic_description="Are there open inventory exceptions for SKU X?",
                rationale="Validation harness"
            ),
            core_identities={"inventory.entity.sku"},
            semantic_constraints=[
                SemanticConstraint(identity="inventory.entity.sku", constraint_type="ENTITY", operator="EQUALS", bound_value="SKU-123")
            ]
        ),
        resolution_strategy=ResolutionStatus.EXACT_MATCH_CAPABILITY,
        authorization_context="Bearer valid_token"
    )
    resolution = CapabilityResolutionResult(requirement_id="req-exception", status=ResolutionStatus.EXACT_MATCH_CAPABILITY, resolved_capabilities=["urn:aarambooks:inventory:capability:exception_status"])
    evidence = await assembler.assemble_evidence(req, resolution)
    
    assert len(evidence) == 1
    assert evidence[0].gap_semantics == "EVIDENCE_SUFFICIENT"
    assert evidence[0].data_payload["open_exceptions"] == 2
    assert evidence[0].provenance.source_system == "urn:aaram:source:inventory"
    
    request_made = http_client.requests[-1]
    assert request_made["json_payload"]["capability_urn"] == "urn:aarambooks:inventory:capability:exception_status"
