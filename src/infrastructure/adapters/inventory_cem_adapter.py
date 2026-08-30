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
        print(f"\n[ADAPTER DEBUG] req_data: {req_data}", flush=True)
        
        query_lower = query.lower()
        if "history" in query_lower or "ledger" in query_lower or "last week" in query_lower:
            target_urn = "urn:aarambooks:inventory:capability:ledger"
        elif "jobwork" in query_lower or "vendor" in query_lower or "pending with" in query_lower:
            target_urn = "urn:aarambooks:inventory:capability:jobwork_status"
        elif "exception" in query_lower or "mismatch" in query_lower:
            target_urn = "urn:aarambooks:inventory:capability:exception_status"
        else:
            target_urn = "urn:aarambooks:inventory:capability:balance"
            
        extracted_constraints = []
        
        entities = req_data.get("entities", [])
        scope_data = req_data.get("scope") or {}
        
        if not entities:
            import re
            # Extract SKU like 126BS or similar pattern
            sku_match = re.search(r'\b(?:sku[:\s=]*)?([0-9]+[A-Za-z0-9_-]*|[A-Za-z]+[0-9]+[A-Za-z0-9_-]*)\b', query, re.IGNORECASE)
            if sku_match:
                candidate = sku_match.group(1)
                stop_words = {"what", "is", "the", "stock", "balance", "for", "sku", "show", "me", "inventory", "ledger", "status", "at", "vendor", "are", "there", "any", "exceptions", "on"}
                if candidate.lower() not in stop_words:
                    entities.append({"original_expression": candidate, "source": "INFERRED", "inferred_type": "sku"})
                    
        for e in entities:
            expr = e.get("original_expression", "")
            # Basic fallback mapping
            if target_urn == "urn:aarambooks:inventory:capability:jobwork_status" and (expr.startswith("V-") or "vendor" in expr.lower()):
                extracted_constraints.append({"identity": "inventory.entity.jobwork_vendor", "operator": "EQUALS", "bound_value": expr})
            elif target_urn == "urn:aarambooks:inventory:capability:ledger" and expr in ["today", "yesterday", "last week", "this month"]:
                extracted_constraints.append({"identity": "inventory.temporal.posting_date", "operator": "EQUALS", "bound_value": expr})
            else:
                extracted_constraints.append({"identity": "inventory.entity.sku", "operator": "EQUALS", "bound_value": expr})
                
        if target_urn == "urn:aarambooks:inventory:capability:jobwork_status" and not any(c.get("identity") == "inventory.entity.jobwork_vendor" for c in extracted_constraints):
            import re
            v_match = re.search(r'\b(?:vendor\s+)?(V-[0-9]+)\b', query, re.IGNORECASE)
            if v_match:
                extracted_constraints.append({"identity": "inventory.entity.jobwork_vendor", "operator": "EQUALS", "bound_value": v_match.group(1)})
            
        if scope_data and scope_data.get("scope_expression"):
            expr = scope_data.get("scope_expression")
            if expr and expr.lower() not in ["all", "all warehouses", "global", "any", "all warehouse"]:
                extracted_constraints.append({"identity": "inventory.entity.warehouse", "operator": "EQUALS", "bound_value": expr})
            
        for cond in req_data.get("conditions", []):
            extracted_constraints.append({"identity": "inventory.capability.balance", "operator": cond.get("operator", "EQUALS"), "bound_value": cond.get("value")})
            
        matching_cap = next((c for c in self._capabilities if (c.metadata or {}).get("urn") == target_urn), None)
        if not matching_cap:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                evidence=[],
                execution_limitations=[{"missing_parameter": target_urn, "reason": "Capability not certified."}]
            )

        required_identities = (matching_cap.metadata or {}).get("required_constraints", [])
        extracted_identities = [c.get("identity") for c in extracted_constraints]
        
        missing_required = [req for req in required_identities if req not in extracted_identities]
        if missing_required:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                evidence=[],
                execution_limitations=[{"missing_parameter": req, "reason": "Missing required constraint"} for req in missing_required]
            )
            
        req_id = str(uuid.uuid4())
        evidence_req = EvidenceRequirement(
            requirement_id=req_id,
            semantic_description=query,
            necessity="REQUIRED",
            rationale="User request"
        )
        
        resolved_req = ResolvedSemanticRequirement(
            requirement_id=req_id,
            original_requirement=evidence_req,
            core_identities=set(extracted_identities),
            semantic_constraints=[],
            semantic_gaps=[]
        )
        
        resolved_req.semantic_constraints.append(
            SemanticConstraint(
                identity=matching_cap.concept_id,
                constraint_type=matching_cap.concept_type,
                operator="EQUALS",
                bound_value=None
            )
        )
        
        ALLOWED_OPERATORS = {"EQUALS", "NOT_EQUALS", "GREATER_THAN", "GREATER_THAN_OR_EQUAL", "LESS_THAN", "LESS_THAN_OR_EQUAL", "IN", "NOT_IN", "BETWEEN"}

        for c in extracted_constraints:
            identity = c.get("identity")
            operator = c.get("operator", "EQUALS")
            
            if operator not in ALLOWED_OPERATORS:
                return BusinessEvidenceResponse(
                    status=BusinessRealityStatus.EXECUTION_LIMITATION,
                    evidence=[],
                    execution_limitations=[{"missing_parameter": operator, "reason": "Unsupported operator"}]
                )

            resolved_req.semantic_constraints.append(
                SemanticConstraint(
                    identity=identity,
                    constraint_type="ENTITY" if "entity" in identity else ("CAPABILITY" if "capability" in identity else "TEMPORAL"),
                    operator=operator,
                    bound_value=c.get("bound_value")
                )
            )

        # Execute legacy pipeline
        print(f"\n[ADAPTER DEBUG] Executing pipeline with: {resolved_req.core_identities}", flush=True)
        import time
        cem_start = time.time()
        evidence_package = await self._brain.execute_requirements([resolved_req], auth_context)
        cem_duration = time.time() - cem_start
        print(f"[BENCHMARK] CEM Data Fetch took {cem_duration:.2f} seconds", flush=True)
        print(f"[ADAPTER DEBUG] Result sufficiency: {evidence_package.sufficiency_assessment}", flush=True)
        
        # Translate legacy EvidencePackage to BusinessEvidenceResponse
        payload = None
        for item in evidence_package.evidence_items:
            ident = getattr(item, "semantic_identity", "") or ""
            if (ident in target_urn or target_urn.endswith(ident)) and getattr(item, "data_payload", None):
                payload = item.data_payload
                break
                
        if not payload and evidence_package.evidence_items:
            for item in evidence_package.evidence_items:
                if getattr(item, "data_payload", None):
                    payload = item.data_payload
                    break
            
        if not payload and evidence_package.sufficiency_assessment == "INSUFFICIENT":
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
                evidence_data=None,
                execution_limitations=[{"missing_parameter": "data", "reason": "Insufficient evidence"}]
            )
            
        return BusinessEvidenceResponse(
            status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
            evidence_data=payload,
            execution_limitations=[]
        )
