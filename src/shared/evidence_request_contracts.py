from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel

from src.shared.requirement_classification_contracts import ClassifiedRequirement

class RefinementContext(BaseModel):
    """
    Context provided by Brain Core during the ONE permitted refinement pass (R-6).
    Instructs CEM on how to broaden or refine execution based on the first pass.
    """
    instruction: str
    accepted_candidates: List[str] = [] # Opaque business IDs provided by CEM in pass 1

class AbstractEvidenceRequest(BaseModel):
    """
    R-3: Brain -> CEM Capability & Evidence Request contract.
    Carries the full conversational understanding and classification without 
    any physical schema knowledge.
    """
    classified_requirement: ClassifiedRequirement
    refinement_context: Optional[RefinementContext] = None

class BusinessRealityStatus(str, Enum):
    CAPABILITY_AVAILABLE = "CAPABILITY_AVAILABLE"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    ENTITY_RESOLVED = "ENTITY_RESOLVED"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    EVIDENCE_AVAILABLE = "EVIDENCE_AVAILABLE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
    EXECUTION_LIMITATION = "EXECUTION_LIMITATION"

class CandidateEntity(BaseModel):
    """
    A possible physical entity matched by CEM during discovery.
    business_id is strictly an opaque string to Brain.
    """
    semantic_reference: str
    business_id: str
    business_name: str
    confidence: float

class ExecutionLimitation(BaseModel):
    """
    Factual report of a physical limitation preventing execution.
    """
    missing_parameter: str
    reason: str

class BusinessEvidenceResponse(BaseModel):
    """
    R-3: CEM -> Brain Response contract.
    Returns business reality and factual evidence to Brain, without
    dictating conversational behavior.
    """
    status: BusinessRealityStatus
    evidence_data: Optional[Dict[str, Any]] = None
    
    # Discovery Feedback
    resolved_candidates: Dict[str, List[CandidateEntity]] = {}
    capabilities_discovered: List[str] = []
    execution_limitations: List[ExecutionLimitation] = []
