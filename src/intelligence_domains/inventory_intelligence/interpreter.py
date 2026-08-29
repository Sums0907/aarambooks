from typing import Any, Dict, Union
from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
from src.shared.conversational_contracts import ConversationalResponse, ConversationalResponseType
from src.shared.decision_contracts import DecisionResponse, DecisionStatus

class InventoryInterpreter:
    """
    R-8 Interpreter for the Inventory Intelligence Domain.
    Deterministically translates structured BusinessEvidenceResponse into a
    ConversationalResponse, preserving boundaries (no mutation, no autonomous resolution).
    """

    async def interpret(self, response: Union[BusinessEvidenceResponse, DecisionResponse]) -> ConversationalResponse:
        if isinstance(response, DecisionResponse):
            if response.status == DecisionStatus.CONFIRMATION_REQUIRED:
                return ConversationalResponse(
                    response_type=ConversationalResponseType.CLARIFICATION_REQUIRED,
                    message="Are you sure you want to proceed with this action?",
                    render_directives={"nonce": response.confirmation_context.nonce} if response.confirmation_context else None
                )
            elif response.status == DecisionStatus.REJECTED:
                return ConversationalResponse(
                    response_type=ConversationalResponseType.EXECUTION_LIMITATION,
                    message="Action was cancelled or expired."
                )
            return ConversationalResponse(
                response_type=ConversationalResponseType.SUCCESS,
                message="Decision processed."
            )

        status = response.status
        
        # 1. Multiple Candidates -> Clarification Required
        if status == BusinessRealityStatus.MULTIPLE_CANDIDATES:
            options = []
            for semantic_ref, candidates in response.resolved_candidates.items():
                for candidate in candidates:
                    options.append({
                        "id": candidate.business_id,
                        "name": candidate.business_name,
                        "semantic_reference": semantic_ref
                    })
            return ConversationalResponse(
                response_type=ConversationalResponseType.CLARIFICATION_REQUIRED,
                message="Multiple matches found. Please select one to proceed.",
                clarification_options=options
            )
            
        # 2. Execution Limitation -> Clarification or Limitation
        if status == BusinessRealityStatus.EXECUTION_LIMITATION:
            missing_params = []
            reasons = []
            for limitation in response.execution_limitations:
                if "missing_parameter" in limitation.model_dump() and limitation.missing_parameter:
                    missing_params.append(limitation.missing_parameter)
                if limitation.reason:
                    reasons.append(limitation.reason)
            
            if missing_params:
                # Missing parameter implies clarification is needed from the user
                return ConversationalResponse(
                    response_type=ConversationalResponseType.CLARIFICATION_REQUIRED,
                    message="I need more information to proceed.",
                    missing_parameters=missing_params
                )
            else:
                # Pure business rejection
                reason_str = "; ".join(reasons) if reasons else "Action was rejected by the business rules."
                return ConversationalResponse(
                    response_type=ConversationalResponseType.EXECUTION_LIMITATION,
                    message=f"Cannot execute action: {reason_str}"
                )

        # 3. Success branches
        if status in (
            BusinessRealityStatus.CAPABILITY_AVAILABLE,
            BusinessRealityStatus.ENTITY_RESOLVED,
            BusinessRealityStatus.EVIDENCE_AVAILABLE,
            BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
            BusinessRealityStatus.PARTIAL_EVIDENCE
        ):
            if status == BusinessRealityStatus.EVIDENCE_UNAVAILABLE:
                msg = "No evidence or records found matching your request."
            else:
                msg = "Request processed successfully."
                
            return ConversationalResponse(
                response_type=ConversationalResponseType.SUCCESS,
                message=msg,
                render_directives={"data": response.evidence_data} if response.evidence_data else None
            )
            
        # 4. Fallback for any unexpected entity failure
        if status == BusinessRealityStatus.ENTITY_NOT_FOUND:
            return ConversationalResponse(
                response_type=ConversationalResponseType.EXECUTION_LIMITATION,
                message="Could not find the requested entity in the system."
            )
            
        # 5. Catch-all fallback
        return ConversationalResponse(
            response_type=ConversationalResponseType.EXECUTION_LIMITATION,
            message=f"Unhandled status: {status}"
        )
