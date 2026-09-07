import json
from .contracts import NDRReportRow

class NDRReportProjection:
    """Projects immutable NDR Intelligence Results into deterministic Report Rows."""
    
    @staticmethod
    def project(result_doc: dict) -> NDRReportRow:
        authorized_action = result_doc.get("authorized_action", "NONE")
        
        # Deterministic Derivation of Manual Guidance
        guidance = "No action required."
        if authorized_action != "NONE":
            guidance = f"Manually perform the recommended {authorized_action} action in the ShopDeck main ecosystem."
            
        return NDRReportRow(
            normalization_id=result_doc.get("normalization_id", ""),
            brain_decision_id=result_doc.get("brain_decision_id"),
            awb_no=result_doc.get("target_identity", ""),
            ndr_reason=result_doc.get("semantic_mapping_metadata", {}).get("ndr_reason", ""),
            diagnosis_category=result_doc.get("diagnosis", "NOT_AVAILABLE"),
            risk_score=result_doc.get("risk_score", "NOT_AVAILABLE"),
            recommended_action=authorized_action,
            action_parameters=json.dumps(result_doc.get("action_parameters", {})),
            reasoning=result_doc.get("reasoning", ""),
            manual_action_guidance=guidance,
            expected_business_benefit="NOT_AVAILABLE"
        )
