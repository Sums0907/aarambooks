import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.brain_core.classification.classifier import RequirementClassifier

async def run():
    mock_gateway = AsyncMock()
    # Need to simulate the classifier JSON output correctly
    mock_gateway.generate.return_value = MagicMock(content='[{"component_reference": "12345", "classification": "MANDATORY"}]')
    
    ndr_orch = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=AsyncMock(),
        memory=AsyncMock(),
        azm_provider=MagicMock()
    )
    
    mock_id_resolver = MagicMock()
    mock_id_resolver.resolve.return_value = ndr_orch
    
    # We need a proper mock adapter
    mock_adapter = AsyncMock()
    from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
    mock_adapter.execute.return_value = BusinessEvidenceResponse(status=BusinessRealityStatus.EVIDENCE_AVAILABLE, retrieved_evidence={"mock": "data"})
    
    mock_cem_resolver = MagicMock()
    mock_cem_resolver.resolve.return_value = mock_adapter

    rabta = RabtaOrchestrator(
        id_resolver=mock_id_resolver,
        cem_resolver=mock_cem_resolver,
        classifier=RequirementClassifier(mock_gateway),
        memory_provider=AsyncMock()
    )
    
    response = await rabta.process_query(
        query="What is the NDR status of AWB 12345?",
        id_urn="urn:aarambooks:intelligence:ndr",
        cem_urn="urn:aarambooks:cem:ndr",
        auth_context="test_auth",
        session_id="session_1"
    )
    print("TYPE:", type(response))
    print("RESPONSE:", response)

asyncio.run(run())
