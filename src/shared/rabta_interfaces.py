from typing import Protocol, Any, List, Optional, Union
from src.shared.conversational_contracts import ConversationalUnderstanding, ConversationalResponse
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessEvidenceResponse
from src.shared.memory_contracts import ConversationTurn
from src.shared.decision_contracts import DecisionResponse

class IntelligenceDomainProvider(Protocol):
    """
    Generic boundary for an Intelligence Domain (ID).
    Provides cognitive semantics and conversational understanding for a specific business domain.
    """
    async def extract_understanding(self, query: str, history: Optional[List[ConversationTurn]] = None) -> ConversationalUnderstanding:
        ...

    async def interpret_evidence(self, response: Union[BusinessEvidenceResponse, DecisionResponse]) -> ConversationalResponse:
        ...

class IntelligenceDomainResolver(Protocol):
    """
    Generic boundary for resolving an Intelligence Domain by its URN.
    """
    def resolve(self, id_urn: str) -> IntelligenceDomainProvider:
        ...

class ContextExecutionAdapter(Protocol):
    """
    Generic boundary for a Context Execution Module (CEM).
    Executes the abstract evidence request against the physical business system.
    """
    async def execute_evidence_request(self, request: AbstractEvidenceRequest, auth_context: str) -> BusinessEvidenceResponse:
        ...

class ContextExecutionResolver(Protocol):
    """
    Generic boundary for resolving a CEM by its URN.
    """
    def resolve(self, cem_urn: str) -> ContextExecutionAdapter:
        ...
