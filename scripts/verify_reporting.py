import os
from datetime import datetime, UTC
from src.intelligence_domains.ndr.reporting.contracts import NDRReportRow
from src.intelligence_domains.ndr.reporting.generator import NDRReportGenerator

def main():
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    generator = NDRReportGenerator(reports_dir)
    
    now = datetime.now(UTC)
    
    row1 = NDRReportRow(
        normalization_id="norm_123",
        brain_decision_id="dec_456",
        awb_no="AWB_TEST_1",
        ndr_reason="Customer unavailable",
        diagnosis_category="NOT_AVAILABLE",
        risk_score="NOT_AVAILABLE",
        recommended_action="seller_reattempt",
        action_parameters='{"date": "tomorrow"}',
        reasoning="High value order",
        manual_action_guidance="Manually perform the recommended seller_reattempt action in the ShopDeck main ecosystem."
    )
    
    row2 = NDRReportRow(
        normalization_id="norm_456",
        brain_decision_id="dec_789",
        awb_no="AWB_TEST_2",
        ndr_reason="Refused delivery",
        diagnosis_category="NOT_AVAILABLE",
        risk_score="NOT_AVAILABLE",
        recommended_action="courier_dispute",
        action_parameters='{"reason": "fake attempt"}',
        reasoning="Repeated fake attempts",
        manual_action_guidance="Manually perform the recommended courier_dispute action in the ShopDeck main ecosystem."
    )
    
    rows = [row1, row2]
    
    # 1. Generate CSV & PDF
    csv_path1 = generator.generate_csv("ndr_action_report_V1", rows)
    pdf_path1 = generator.generate_pdf("ndr_action_report_V1", "Last 24h", rows)
    print(f"Generated CSV: {csv_path1}")
    print(f"Generated PDF: {pdf_path1}")
    
    # 2. Verify Determinism
    csv_path2 = generator.generate_csv("ndr_action_report_V1_dup", rows)
    with open(csv_path1, "rb") as f1, open(csv_path2, "rb") as f2:
        if f1.read() == f2.read():
            print("PASS: CSV Generation is deterministically identical byte-for-byte.")
        else:
            print("FAIL: CSV Generation is not deterministic.")
            
if __name__ == "__main__":
    main()
