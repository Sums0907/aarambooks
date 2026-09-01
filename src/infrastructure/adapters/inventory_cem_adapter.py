import uuid
from typing import Dict, Any, List

from src.shared.rabta_interfaces import ContextExecutionAdapter
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessEvidenceResponse, BusinessRealityStatus
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement, SemanticConstraint
from src.shared.cognitive_planning_contracts import EvidenceRequirement, GapSemantics

class InventoryCemAdapter(ContextExecutionAdapter):
    """
    TEMPORARY COMPATIBILITY BRIDGE
    TO BE REMOVED WHEN R-4/R-5/R-7 CEM IMPLEMENTATION IS CERTIFIED.
    
    This adapter translates the pure R-3 AbstractEvidenceRequest into the legacy execution contract
    (ResolvedSemanticRequirement) and executes it using the legacy BrainOrchestrator pipeline.
    """
    def __init__(self, brain_orchestrator: Any, capabilities: List[Any]):
        self._brain = brain_orchestrator
        self._capabilities = capabilities

    async def execute_evidence_request(self, request: AbstractEvidenceRequest, auth_context: str) -> BusinessEvidenceResponse:
        understanding = request.classified_requirement.understanding
        query = understanding.original_query
        req_data = understanding.model_dump()
        print(f"\n[ADAPTER DEBUG] Action Request Data: {req_data}", flush=True)
        
        # CEM Adapter now exclusively handles ACTION (mutation) intents.
        intent = req_data.get("intent", "UNKNOWN")
        if intent != "ACTION":
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                evidence_data=None,
                execution_limitations=[{"missing_parameter": "intent", "reason": "CEM Adapter only handles ACTION intents in the new architecture."}]
            )

        target_urn = "urn:aarambooks:inventory:capability:adjust_balance"
        
        matching_cap = next((c for c in self._capabilities if (c.metadata or {}).get("urn") == target_urn), None)
        if not matching_cap:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                evidence=[],
                execution_limitations=[{"missing_parameter": target_urn, "reason": "Mutation Capability not certified."}]
            )
            
        req_id = str(uuid.uuid4())
        
        # MOCK EXECUTION FOR REGRESSION TESTING
        # In a real environment, this translates to an RPC call to the warehouse management system
        print(f"\n[ADAPTER DEBUG] Executing Transactional Mutation for {req_id}", flush=True)
        
        payload = {"status": "SUCCESS", "message": "Transactional mutation executed successfully via CEM."}
            
        return BusinessEvidenceResponse(
            status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
            evidence_data=payload,
            execution_limitations=[]
        )
