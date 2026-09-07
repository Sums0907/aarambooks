fpath1 = "tests/intelligence_domains/ndr/test_ndr_orchestration.py"
with open(fpath1, "r") as f:
    content1 = f.read()

fix1 = """    from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
    from unittest.mock import AsyncMock
    mock_cem_adapter = AsyncMock()
    mock_cem_adapter.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        retrieved_evidence={"shipment_ndr_reports": [{"awb_no": "12345"}]}
    )
    mock_cem_resolver = MagicMock(spec=ContextExecutionResolver)
    mock_cem_resolver.resolve.return_value = mock_cem_adapter"""

content1 = content1.replace("    mock_cem_resolver = MagicMock(spec=ContextExecutionResolver)", fix1)

with open(fpath1, "w") as f:
    f.write(content1)

fpath2 = "tests/intelligence_domains/ndr/test_ndr_real_integration.py"
with open(fpath2, "r") as f:
    content2 = f.read()

fix2 = """    from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
    from unittest.mock import AsyncMock
    mock_cem_adapter = AsyncMock()
    mock_cem_adapter.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        retrieved_evidence={"shipment_ndr_reports": [{"awb_no": "12345"}]}
    )
    mock_cem_resolver = MagicMock()
    mock_cem_resolver.resolve.return_value = mock_cem_adapter

    rabta = RabtaOrchestrator(
        id_resolver=mock_id_resolver,
        cem_resolver=mock_cem_resolver,"""

content2 = content2.replace("""    rabta = RabtaOrchestrator(
        id_resolver=mock_id_resolver,
        cem_resolver=MagicMock(),""", fix2)

with open(fpath2, "w") as f:
    f.write(content2)
