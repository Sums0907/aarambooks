import pytest
import asyncio
from datetime import datetime, UTC, timedelta
from src.intelligence_domains.ndr.reporting.contracts import NDRReportRow
from src.intelligence_domains.ndr.reporting.projection import NDRReportProjection
from src.intelligence_domains.ndr.reporting.service import NDRReportService

@pytest.mark.asyncio
async def test_report_projection_and_eligibility():
    # Test projection
    doc = {
        "normalization_id": "norm_123",
        "brain_decision_id": "dec_456",
        "target_identity": "AWB_TEST",
        "semantic_mapping_metadata": {"ndr_reason": "Customer not home"},
        "diagnosis": "NOT_AVAILABLE",
        "risk_score": "NOT_AVAILABLE",
        "authorized_action": "seller_reattempt",
        "action_parameters": {"date": "tomorrow"},
        "reasoning": "High value order",
        "normalization_status": "COMPLETED",
        "completed_at": datetime.now(UTC)
    }
    
    row = NDRReportProjection.project(doc)
    assert row.normalization_id == "norm_123"
    assert row.manual_action_guidance == "Manually perform the recommended seller_reattempt action in the ShopDeck main ecosystem."
    assert row.diagnosis_category == "NOT_AVAILABLE"
    assert row.expected_business_benefit == "NOT_AVAILABLE"
    
    # Generate CSV determinism check
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        service = NDRReportService(output_dir=d)
        csv_path1 = service.generator.generate_csv("rep1", [row])
        csv_path2 = service.generator.generate_csv("rep2", [row])
        
        with open(csv_path1, 'rb') as f1, open(csv_path2, 'rb') as f2:
            assert f1.read() == f2.read()
