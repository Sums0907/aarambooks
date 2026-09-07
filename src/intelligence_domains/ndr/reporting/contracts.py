from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class NDRReportRow(BaseModel):
    """Canonical Report Projection Contract - Maps exactly from Intelligence Result."""
    
    # SYSTEM SOURCE FIELDS
    normalization_id: str
    brain_decision_id: Optional[str] = None
    awb_no: str
    ndr_reason: Optional[str] = None
    diagnosis_category: Optional[str] = None
    risk_score: Optional[str] = None
    recommended_action: str
    action_parameters: str = ""
    reasoning: Optional[str] = None
    
    # DETERMINISTIC DERIVATION FIELDS
    manual_action_guidance: str
    
    # NOT_AVAILABLE FIELDS
    expected_business_benefit: str = "NOT_AVAILABLE"
    
    # OPERATOR FIELDS
    action_taken: str = ""
    operator_notes: str = ""
