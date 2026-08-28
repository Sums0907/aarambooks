from enum import Enum
from typing import Dict, Any, Optional, Protocol, List
from pydantic import BaseModel
from src.shared.cognitive_planning_contracts import ProvenanceMetadata

class ContextRetrievalStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    UNAUTHORIZED = "UNAUTHORIZED"
    ERROR = "ERROR"

class ContextCapabilityResult(BaseModel):
    status: ContextRetrievalStatus
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    provenance_metadata: Optional[ProvenanceMetadata] = None

class ContextCapabilityProvider(Protocol):
    async def fetch_capability_context(
        self, capability_urn: str, constraints: List[Any], authorization: Optional[str]
    ) -> ContextCapabilityResult:
        ...
