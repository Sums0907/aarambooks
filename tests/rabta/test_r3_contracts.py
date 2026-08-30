import pytest
from src.shared.conversational_contracts import (
    ConversationalUnderstanding, ConversationalIntent, InformationSource, 
    SemanticEntityReference
)
from src.shared.requirement_classification_contracts import (
    ClassifiedRequirement, RequirementClass, ClassifiedComponent
)
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest, RefinementContext, BusinessEvidenceResponse,
    BusinessRealityStatus, CandidateEntity, ExecutionLimitation
)

def test_r3_abstract_evidence_request_preserves_r1_and_r2():
    # R-1 Understanding
    cu = ConversationalUnderstanding(
        original_query="Give me stock of Blush Bloom",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="Blush Bloom", source=InformationSource.EXPLICIT)
        ]
    )
    
    # R-2 Classification
    cr = ClassifiedRequirement(
        understanding=cu,
        component_classifications=[
            ClassifiedComponent(
                component_reference="Blush Bloom",
                classification=RequirementClass.MANDATORY,
                reason="Core entity"
            )
        ]
    )
    
    # R-3 Request
    req = AbstractEvidenceRequest(classified_requirement=cr)
    
    # Assert preservation
    assert req.classified_requirement.understanding.intent == ConversationalIntent.RETRIEVE
    assert req.classified_requirement.understanding.entities[0].original_expression == "Blush Bloom"
    assert req.classified_requirement.component_classifications[0].classification == RequirementClass.MANDATORY
    
    # Assert no UUIDs or schema leaked in
    req_dump = req.model_dump()
    assert "uuid" not in req_dump
    assert "schema" not in req_dump

def test_r3_refinement_context_supports_opaque_identifiers():
    ref_ctx = RefinementContext(
        instruction="Proceed with 50ml candidate",
        accepted_candidates=["opaque_uuid_xyz_123"]
    )
    
    req = AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(
                original_query="Give me stock",
                intent=ConversationalIntent.RETRIEVE
            ),
            component_classifications=[]
        ),
        refinement_context=ref_ctx
    )
    
    assert "opaque_uuid_xyz_123" in req.refinement_context.accepted_candidates

def test_r3_business_evidence_response_represents_facts():
    # Test MULTIPLE_CANDIDATES
    resp1 = BusinessEvidenceResponse(
        status=BusinessRealityStatus.MULTIPLE_CANDIDATES,
        resolved_candidates={
            "Blush Bloom": [
                CandidateEntity(semantic_reference="Blush Bloom", business_id="ID-1", business_name="BB 50ml", confidence=0.9),
                CandidateEntity(semantic_reference="Blush Bloom", business_id="ID-2", business_name="BB 100ml", confidence=0.8)
            ]
        }
    )
    assert resp1.status == BusinessRealityStatus.MULTIPLE_CANDIDATES
    assert len(resp1.resolved_candidates["Blush Bloom"]) == 2
    
    # Test EXECUTION_LIMITATION
    resp2 = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EXECUTION_LIMITATION,
        execution_limitations=[
            ExecutionLimitation(missing_parameter="warehouse_id", reason="API requires a warehouse bound")
        ]
    )
    assert resp2.status == BusinessRealityStatus.EXECUTION_LIMITATION
    assert resp2.execution_limitations[0].missing_parameter == "warehouse_id"
    
    # Test EVIDENCE_AVAILABLE
    resp3 = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"stock_quantity": 42}
    )
    assert resp3.status == BusinessRealityStatus.EVIDENCE_AVAILABLE
    assert resp3.evidence_data["stock_quantity"] == 42
