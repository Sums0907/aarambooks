import pytest
import asyncio
from typing import Dict, Any

from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
    CandidateEntity,
    ExecutionLimitation,
    RefinementContext
)
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.conversational_contracts import ConversationalUnderstanding

class DomainNeutralMockCEM:
    """
    A completely generic mock CEM proving that R-4.0 abstraction can be implemented
    without any Inventory, Packing, Sales, or DB-specific schema knowledge.
    """
    def __init__(self, desired_response: BusinessEvidenceResponse):
        self.desired_response = desired_response
        self.last_received_request = None
        self.last_received_auth = None

    async def execute_evidence_request(self, request: AbstractEvidenceRequest, auth_context: str) -> BusinessEvidenceResponse:
        self.last_received_request = request
        self.last_received_auth = auth_context
        return self.desired_response

@pytest.fixture
def sample_classified_req():
    understanding = ConversationalUnderstanding(
        original_query="Show me the generic entity",
        intent="RETRIEVE"
    )
    return ClassifiedRequirement(
        understanding=understanding,
        components=[]
    )

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_capability_available(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.CAPABILITY_AVAILABLE,
        capabilities_discovered=["urn:test:capability"]
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert cem.last_received_request == req
    assert cem.last_received_auth == "test_user"
    assert resp.status == BusinessRealityStatus.CAPABILITY_AVAILABLE
    assert "urn:test:capability" in resp.capabilities_discovered

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_entity_resolved(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    candidates = {
        "entity_1": [
            CandidateEntity(
                semantic_reference="generic entity",
                business_id="opaque-id-123",
                business_name="Generic Entity One",
                confidence=1.0
            )
        ]
    }
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.ENTITY_RESOLVED,
        resolved_candidates=candidates
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert resp.status == BusinessRealityStatus.ENTITY_RESOLVED
    assert len(resp.resolved_candidates["entity_1"]) == 1
    assert resp.resolved_candidates["entity_1"][0].business_id == "opaque-id-123"

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_multiple_candidates(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    candidates = {
        "entity_1": [
            CandidateEntity(
                semantic_reference="generic entity",
                business_id="opaque-id-1",
                business_name="Generic Entity One",
                confidence=0.8
            ),
            CandidateEntity(
                semantic_reference="generic entity",
                business_id="opaque-id-2",
                business_name="Generic Entity Two",
                confidence=0.8
            )
        ]
    }
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.MULTIPLE_CANDIDATES,
        resolved_candidates=candidates
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert resp.status == BusinessRealityStatus.MULTIPLE_CANDIDATES
    assert len(resp.resolved_candidates["entity_1"]) == 2

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_entity_not_found(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.ENTITY_NOT_FOUND
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert resp.status == BusinessRealityStatus.ENTITY_NOT_FOUND

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_execution_limitation(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EXECUTION_LIMITATION,
        execution_limitations=[
            ExecutionLimitation(missing_parameter="required_param", reason="Missing mandatory input")
        ]
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert resp.status == BusinessRealityStatus.EXECUTION_LIMITATION
    assert len(resp.execution_limitations) == 1
    assert resp.execution_limitations[0].missing_parameter == "required_param"

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_evidence_available(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"generic_key": "generic_value"}
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert resp.status == BusinessRealityStatus.EVIDENCE_AVAILABLE
    assert resp.evidence_data == {"generic_key": "generic_value"}

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_partial_evidence(sample_classified_req):
    req = AbstractEvidenceRequest(classified_requirement=sample_classified_req)
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.PARTIAL_EVIDENCE,
        evidence_data={"generic_key": "partial_value"}
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert resp.status == BusinessRealityStatus.PARTIAL_EVIDENCE
    assert resp.evidence_data == {"generic_key": "partial_value"}

@pytest.mark.asyncio
async def test_r4_0_cem_abstraction_accepts_refinement_context(sample_classified_req):
    refinement = RefinementContext(
        instruction="Broaden search",
        accepted_candidates=["opaque-id-1"]
    )
    req = AbstractEvidenceRequest(
        classified_requirement=sample_classified_req,
        refinement_context=refinement
    )
    
    expected_response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"generic_key": "generic_value"}
    )
    
    cem = DomainNeutralMockCEM(desired_response=expected_response)
    resp = await cem.execute_evidence_request(req, "test_user")
    
    assert cem.last_received_request.refinement_context is not None
    assert cem.last_received_request.refinement_context.instruction == "Broaden search"
    assert cem.last_received_request.refinement_context.accepted_candidates == ["opaque-id-1"]
