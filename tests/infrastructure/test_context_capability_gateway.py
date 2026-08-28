import pytest
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from pydantic import BaseModel

from src.infrastructure.context_capability_gateway import (
    ContextCapabilityGateway,
    GatewayConfiguration,
    HttpClient,
    HttpResponse
)
from src.shared.context_contracts.provider import ContextRetrievalStatus, ContextCapabilityResult
from src.shared.context_contracts.capability import CapabilityURN
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement, SemanticConstraint
from src.shared.cognitive_planning_contracts import EvidenceRequirement, ProvenanceMetadata

class MockGatewayConfiguration(GatewayConfiguration):
    def __init__(self, routing: Dict[str, str]):
        self._routing = routing
        
    def get_endpoint(self, urn: CapabilityURN) -> Optional[str]:
        return self._routing.get(urn)

class MockHttpClient(HttpClient):
    def __init__(self, response_queue: list[HttpResponse], record_requests: list[dict]):
        self.response_queue = response_queue
        self.record_requests = record_requests
        
    async def post(self, url: str, headers: Dict[str, str], json_payload: Dict[str, Any]) -> HttpResponse:
        self.record_requests.append({
            "url": url,
            "headers": headers,
            "json_payload": json_payload
        })
        if self.response_queue:
            return self.response_queue.pop(0)
        raise Exception("Mock timeout")

@pytest.fixture
def requirement():
    return ResolvedSemanticRequirement(
        requirement_id="req-generic-1",
        original_requirement=EvidenceRequirement(
            requirement_id="req-generic-1",
            semantic_description="Generic query",
            rationale="Test"
        ),
        core_identities={"generic.entity.test"},
        semantic_constraints=[
            SemanticConstraint(
                identity="generic.entity.test",
                constraint_type="ENTITY",
                operator="EQUALS",
                bound_value="123"
            )
        ]
    )

@pytest.mark.asyncio
async def test_gateway_successful_invocation(requirement):
    urn = "urn:generic:capability:test"
    config = MockGatewayConfiguration({urn: "https://mock.system/api/invoke"})
    
    # Provider returns business SUCCESS
    response_data = {
        "status": "SUCCESS",
        "data": {"mock_metric": 100},
        "provenance_metadata": {
            "source_system": "urn:generic:source:db",
            "retrieval_timestamp": "2026-08-28T12:00:00Z"
        }
    }
    responses = [HttpResponse(status_code=200, json_data=response_data)]
    requests = []
    http_client = MockHttpClient(responses, requests)
    
    gateway = ContextCapabilityGateway(config, http_client)
    
    result = await gateway.invoke_capability(urn, requirement, "user_777")
    
    # 1. Assert Transport execution
    assert len(requests) == 1
    req = requests[0]
    assert req["url"] == "https://mock.system/api/invoke"
    assert req["headers"]["Authorization"] == "Bearer user_777"
    assert "X-Correlation-ID" in req["headers"]
    
    # 2. Assert Canonical Request Payload Serialization (zero interpretation)
    payload = req["json_payload"]
    assert payload["capability_urn"] == urn
    assert payload["requirement"]["requirement_id"] == "req-generic-1"
    assert len(payload["requirement"]["semantic_constraints"]) == 1
    constraint = payload["requirement"]["semantic_constraints"][0]
    assert constraint["identity"] == "generic.entity.test"
    assert constraint["operator"] == "EQUALS"
    assert constraint["bound_value"] == "123"
    
    # 3. Assert Gateway mapped response correctly
    assert result.status == ContextRetrievalStatus.SUCCESS
    assert result.data == {"mock_metric": 100}

@pytest.mark.asyncio
async def test_gateway_data_unavailable(requirement):
    urn = "urn:generic:capability:test"
    config = MockGatewayConfiguration({urn: "https://mock.system/api/invoke"})
    
    # Provider returns business DATA_UNAVAILABLE (zero records)
    response_data = {
        "status": "DATA_UNAVAILABLE",
        "data": {}
    }
    http_client = MockHttpClient([HttpResponse(status_code=200, json_data=response_data)], [])
    gateway = ContextCapabilityGateway(config, http_client)
    
    result = await gateway.invoke_capability(urn, requirement, "user_777")
    
    assert result.status == ContextRetrievalStatus.DATA_UNAVAILABLE

@pytest.mark.asyncio
async def test_gateway_transport_failure(requirement):
    urn = "urn:generic:capability:test"
    config = MockGatewayConfiguration({urn: "https://mock.system/api/invoke"})
    
    # HTTP 500 error from infrastructure
    http_client = MockHttpClient([HttpResponse(status_code=500, text_data="Internal Server Error")], [])
    gateway = ContextCapabilityGateway(config, http_client)
    
    result = await gateway.invoke_capability(urn, requirement, "user_777")
    
    # Gateway translates infrastructure failure to capability ERROR
    assert result.status == ContextRetrievalStatus.ERROR
    assert "Transport error (HTTP 500)" in result.error_message

@pytest.mark.asyncio
async def test_gateway_unauthorized_propagation(requirement):
    urn = "urn:generic:capability:test"
    config = MockGatewayConfiguration({urn: "https://mock.system/api/invoke"})
    
    # Provider returns UNAUTHORIZED business response
    response_data = {
        "status": "UNAUTHORIZED",
        "error_message": "User lacks domain RBAC"
    }
    http_client = MockHttpClient([HttpResponse(status_code=200, json_data=response_data)], [])
    gateway = ContextCapabilityGateway(config, http_client)
    
    result = await gateway.invoke_capability(urn, requirement, "user_777")
    
    assert result.status == ContextRetrievalStatus.UNAUTHORIZED
    assert "RBAC" in result.error_message

@pytest.mark.asyncio
async def test_gateway_missing_configuration(requirement):
    urn = "urn:generic:capability:test"
    config = MockGatewayConfiguration({}) # empty routing
    
    gateway = ContextCapabilityGateway(config, MockHttpClient([], []))
    
    result = await gateway.invoke_capability(urn, requirement, "user_777")
    
    assert result.status == ContextRetrievalStatus.ERROR
    assert "No endpoint configured" in result.error_message

@pytest.mark.asyncio
async def test_gateway_network_exception(requirement):
    urn = "urn:generic:capability:test"
    config = MockGatewayConfiguration({urn: "https://mock.system/api/invoke"})
    
    # Mock timeout exception inside client
    http_client = MockHttpClient([], [])
    gateway = ContextCapabilityGateway(config, http_client)
    
    result = await gateway.invoke_capability(urn, requirement, "user_777")
    
    assert result.status == ContextRetrievalStatus.ERROR
    assert "Transport exception" in result.error_message
