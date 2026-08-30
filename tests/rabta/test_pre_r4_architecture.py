import pytest
import asyncio
from typing import Any
from src.shared.rabta_interfaces import (
    IntelligenceDomainProvider,
    IntelligenceDomainResolver,
    ContextExecutionAdapter,
    ContextExecutionResolver
)
from src.shared.conversational_contracts import ConversationalUnderstanding
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessEvidenceResponse, BusinessRealityStatus
from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.brain_core.classification.classifier import RequirementClassifier
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationResponse

class DummyIDProvider(IntelligenceDomainProvider):
    async def extract_understanding(self, query: str, history=None) -> ConversationalUnderstanding:
        return ConversationalUnderstanding(
            original_query=query,
            intent="SEARCH",
            domain="DUMMY_DOMAIN",
            entities=[],
            attributes=[],
            conditions=[],
            desired_outcome="TEST_OUTCOME",
            user_supplied_criteria=[]
        )
    async def interpret_evidence(self, response: BusinessEvidenceResponse) -> Any:
        return f"DUMMY INTERPRETED: {response.status}"

class DummyIDResolver(IntelligenceDomainResolver):
    def __init__(self, provider):
        self.provider = provider
    def resolve(self, id_urn: str) -> IntelligenceDomainProvider:
        if id_urn == "urn:dummy:id":
            return self.provider
        return None

class DummyCEMAdapter(ContextExecutionAdapter):
    async def execute_evidence_request(self, request: AbstractEvidenceRequest, auth_context: str) -> BusinessEvidenceResponse:
        return BusinessEvidenceResponse(
            status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
            evidence=[{"dummy": "data"}],
            limitations=[]
        )

class DummyCEMResolver(ContextExecutionResolver):
    def __init__(self, adapter):
        self.adapter = adapter
    def resolve(self, cem_urn: str) -> ContextExecutionAdapter:
        if cem_urn == "urn:dummy:cem":
            return self.adapter
        return None

class MockGatewayProvider(ModelGatewayProvider):
    async def generate(self, request: Any) -> GatewayGenerationResponse:
        return GatewayGenerationResponse(
            content='''```json
            [
                {
                    "component_reference": "dummy",
                    "classification": "MANDATORY",
                    "reason": "Test"
                }
            ]
            ```''',
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=15
        )

@pytest.mark.asyncio
async def test_rabta_orchestrator_decoupled_flow():
    # A. Generic ID test & B. Generic CEM test
    # C. Resolver independence: they only know about their specific dummy providers
    id_provider = DummyIDProvider()
    cem_adapter = DummyCEMAdapter()
    id_resolver = DummyIDResolver(id_provider)
    cem_resolver = DummyCEMResolver(cem_adapter)
    
    gateway = MockGatewayProvider()
    classifier = RequirementClassifier(gateway)
    
    # E. No Inventory coupling (no inventory imports here!)
    orchestrator = RabtaOrchestrator(
        id_resolver=id_resolver,
        cem_resolver=cem_resolver,
        classifier=classifier
    )
    
    # D. RABTA independence
    # 11. MOST IMPORTANT ARCHITECTURAL TEST: RabtaOrchestrator -> Dummy ID -> R-2 -> R-3 -> Dummy CEM
    final_answer = await orchestrator.process_query(
        query="Hello dummy",
        id_urn="urn:dummy:id",
        cem_urn="urn:dummy:cem",
        auth_context="user-123"
    )
    
    assert final_answer == "DUMMY INTERPRETED: BusinessRealityStatus.EVIDENCE_AVAILABLE"

@pytest.mark.asyncio
async def test_rabta_orchestrator_missing_urn():
    id_resolver = DummyIDResolver(DummyIDProvider())
    cem_resolver = DummyCEMResolver(DummyCEMAdapter())
    orchestrator = RabtaOrchestrator(
        id_resolver=id_resolver,
        cem_resolver=cem_resolver,
        classifier=RequirementClassifier(MockGatewayProvider())
    )
    
    # Test missing ID
    resp = await orchestrator.process_query("test", "urn:wrong:id", "urn:dummy:cem", "user-123")
    assert "Authorization/Resolution Error" in resp
    
    # Test missing CEM
    resp = await orchestrator.process_query("test", "urn:dummy:id", "urn:wrong:cem", "user-123")
    assert "Authorization/Resolution Error" in resp
