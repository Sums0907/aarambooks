from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from src.shared.context_contracts.capability import CapabilityURN
from src.shared.context_contracts.source import ContextSourceURN

class GapSemantics(str, Enum):
    EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT"
    EVIDENCE_PARTIAL = "EVIDENCE_PARTIAL"
    CONTEXT_CAPABILITY_UNAVAILABLE = "CONTEXT_CAPABILITY_UNAVAILABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    SEMANTIC_KNOWLEDGE_GAP = "SEMANTIC_KNOWLEDGE_GAP"
    DATA_INACCESSIBLE = "DATA_INACCESSIBLE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PROVIDER_EXECUTION_ERROR = "PROVIDER_EXECUTION_ERROR"

class ResolutionStatus(str, Enum):
    EXACT_MATCH_CAPABILITY = "EXACT_MATCH_CAPABILITY"
    DYNAMIC_DISCOVERY_REQUIRED = "DYNAMIC_DISCOVERY_REQUIRED"
    UNRESOLVABLE = "UNRESOLVABLE"

class EvidenceRequirement(BaseModel):
    requirement_id: str
    semantic_description: str
    necessity: str = "REQUIRED" # CRITICAL, SUPPORTING, OPTIONAL
    time_range: Optional[str] = None
    filters: Optional[List[str]] = None
    rationale: str

class EvidencePlan(BaseModel):
    plan_id: str
    original_intent: str
    domain_context: str
    requirements: List[EvidenceRequirement]
    planning_dependencies: Optional[Dict[str, List[str]]] = None
    metadata: Optional[Dict[str, Any]] = None

class EvidencePlanExtension(BaseModel):
    parent_plan_id: str
    extension_id: str
    new_requirements: List[EvidenceRequirement]
    reason_for_extension: str

class ProvenanceMetadata(BaseModel):
    source_system: Optional[ContextSourceURN] = None
    retrieval_timestamp: datetime
    business_timestamp: Optional[datetime] = None
    derivation_metadata: Optional[str] = None

class EvidenceItem(BaseModel):
    item_id: str
    semantic_identity: str
    data_payload: Optional[Dict[str, Any]] = None
    provenance: ProvenanceMetadata
    gap_semantics: GapSemantics = GapSemantics.EVIDENCE_SUFFICIENT
    confidence_quality: Optional[str] = None

class EvidencePackage(BaseModel):
    package_id: str
    plan_id: str
    evidence_items: List[EvidenceItem]
    sufficiency_assessment: str # SUFFICIENT, PARTIAL, INSUFFICIENT
    gaps: List[GapSemantics] = []

class ContextAssemblyRequest(BaseModel):
    request_id: str
    resolved_requirement: Any
    resolution_strategy: ResolutionStatus
    authorization_context: str
    execution_constraints: Optional[Dict[str, Any]] = None

class CapabilityResolutionResult(BaseModel):
    requirement_id: str
    status: ResolutionStatus
    resolved_capabilities: List[CapabilityURN] = Field(default_factory=list)
    resolved_sources: List[ContextSourceURN] = Field(default_factory=list)
