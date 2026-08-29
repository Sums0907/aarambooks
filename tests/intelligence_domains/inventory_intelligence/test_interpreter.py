import pytest
from src.intelligence_domains.inventory_intelligence.interpreter import InventoryInterpreter
from src.shared.evidence_request_contracts import (
    BusinessEvidenceResponse, 
    BusinessRealityStatus,
    CandidateEntity,
    ExecutionLimitation
)
from src.shared.conversational_contracts import ConversationalResponseType

@pytest.mark.asyncio
async def test_interpreter_success():
    interpreter = InventoryInterpreter()
    
    response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={"stock": 100}
    )
    
    result = await interpreter.interpret(response)
    
    assert result.response_type == ConversationalResponseType.SUCCESS
    assert result.message == "Request processed successfully."
    assert result.render_directives == {"data": {"stock": 100}}

@pytest.mark.asyncio
async def test_interpreter_multiple_candidates():
    interpreter = InventoryInterpreter()
    
    response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.MULTIPLE_CANDIDATES,
        resolved_candidates={
            "sku-123": [
                CandidateEntity(semantic_reference="sku-123", business_id="uuid-1", business_name="Item A", confidence=1.0),
                CandidateEntity(semantic_reference="sku-123", business_id="uuid-2", business_name="Item B", confidence=0.8)
            ]
        }
    )
    
    result = await interpreter.interpret(response)
    
    assert result.response_type == ConversationalResponseType.CLARIFICATION_REQUIRED
    assert len(result.clarification_options) == 2
    assert result.clarification_options[0]["id"] == "uuid-1"
    assert result.clarification_options[0]["name"] == "Item A"

@pytest.mark.asyncio
async def test_interpreter_missing_parameter():
    interpreter = InventoryInterpreter()
    
    response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EXECUTION_LIMITATION,
        execution_limitations=[
            ExecutionLimitation(missing_parameter="quantity", reason="Required field")
        ]
    )
    
    result = await interpreter.interpret(response)
    
    assert result.response_type == ConversationalResponseType.CLARIFICATION_REQUIRED
    assert "quantity" in result.missing_parameters

@pytest.mark.asyncio
async def test_interpreter_business_rejection():
    interpreter = InventoryInterpreter()
    
    response = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EXECUTION_LIMITATION,
        execution_limitations=[
            ExecutionLimitation(missing_parameter="", reason="Insufficient stock")
        ]
    )
    
    result = await interpreter.interpret(response)
    
    assert result.response_type == ConversationalResponseType.EXECUTION_LIMITATION
    assert "Insufficient stock" in result.message
