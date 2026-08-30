from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from src.shared.conversational_contracts import ConversationalUnderstanding

class RequirementClass(str, Enum):
    MANDATORY = "MANDATORY"
    OPTIONAL = "OPTIONAL"
    DERIVABLE = "DERIVABLE"
    BROADENABLE = "BROADENABLE" # Kept for later phases (R-6), not assigned by R-2
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"

class ClassifiedComponent(BaseModel):
    """
    Classifies a specific component of the ConversationalUnderstanding 
    (e.g., an entity, attribute, or condition) based purely on its 
    conversational role.
    """
    component_reference: str
    classification: RequirementClass
    reason: str

class ClassifiedRequirement(BaseModel):
    """
    The output of the R-2 Requirement Classification phase.
    Preserves the entire R-1 ConversationalUnderstanding and adds classification
    metadata for components that actually exist in the R-1 output.
    """
    understanding: ConversationalUnderstanding
    component_classifications: List[ClassifiedComponent] = []
    global_classification: Optional[RequirementClass] = None
