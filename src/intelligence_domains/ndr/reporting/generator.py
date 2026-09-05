import csv
import os
from datetime import datetime, UTC
from typing import List
from .contracts import NDRReportRow

class NDRReportGenerator:
    """Deterministic CSV and PDF generator for NDR Action Reports."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_csv(self, report_id: str, rows: List[NDRReportRow]) -> str:
        filepath = os.path.join(self.output_dir, f"{report_id}.csv")
        
        headers = [
            "normalization_id", "brain_decision_id", "awb_no", "ndr_reason",
            "diagnosis_category", "risk_score", "recommended_action",
            "action_parameters", "reasoning", "manual_action_guidance",
            "expected_business_benefit", "action_taken", "operator_notes"
        ]
        
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            # Sort rows deterministically by target identity (AWB)
            sorted_rows = sorted(rows, key=lambda r: r.awb_no)
            for row in sorted_rows:
                writer.writerow([
                    row.normalization_id,
                    row.brain_decision_id or "",
                    row.awb_no,
                    row.ndr_reason or "",
                    row.diagnosis_category or "",
                    row.risk_score or "",
                    row.recommended_action,
                    row.action_parameters,
                    row.reasoning or "",
                    row.manual_action_guidance,
                    row.expected_business_benefit,
                    row.action_taken,
                    row.operator_notes
                ])
                
        return filepath
        
    def _create_binary_pdf(self, filepath: str, text_lines: List[str]):
        """Generates a genuine binary PDF 1.4 file without external libraries."""
        # This writes a minimal but strictly compliant PDF file.
        # Format lines
        stream_content = "BT\n/F1 12 Tf\n10 800 Td\n15 TL\n"
        for line in text_lines:
            # Escape parenthesis
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            stream_content += f"({escaped}) Tj T*\n"
        stream_content += "ET"
        
        stream_len = len(stream_content)
        
        pdf = b"%PDF-1.4\n"
        pdf += b"%\xDE\xAD\xBE\xEF\n" # binary marker
        
        obj1_pos = len(pdf)
        pdf += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        obj2_pos = len(pdf)
        pdf += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        obj3_pos = len(pdf)
        pdf += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
        
        obj4_pos = len(pdf)
        pdf += f"4 0 obj\n<< /Length {stream_len} >>\nstream\n{stream_content}\nendstream\nendobj\n".encode("utf-8")
        
        xref_pos = len(pdf)
        pdf += b"xref\n0 5\n"
        pdf += b"0000000000 65535 f \n"
        pdf += f"{obj1_pos:010} 00000 n \n".encode("utf-8")
        pdf += f"{obj2_pos:010} 00000 n \n".encode("utf-8")
        pdf += f"{obj3_pos:010} 00000 n \n".encode("utf-8")
        pdf += f"{obj4_pos:010} 00000 n \n".encode("utf-8")
        
        pdf += f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("utf-8")
        
        with open(filepath, "wb") as f:
            f.write(pdf)

    def generate_pdf(self, report_id: str, reporting_period: str, rows: List[NDRReportRow]) -> str:
        filepath = os.path.join(self.output_dir, f"{report_id}.pdf")
        
        lines = []
        lines.append("=========================================")
        lines.append("      NDR ACTION REPORT (SUMMARY)      ")
        lines.append("=========================================")
        lines.append(f"Report ID: {report_id}")
        lines.append(f"Generated At: {datetime.now(UTC).isoformat()}")
        lines.append(f"Reporting Period: {reporting_period}")
        lines.append(f"Total NDRs: {len(rows)}")
        lines.append("")
        lines.append("--- ACTION QUEUE ---")
        for row in sorted(rows, key=lambda r: r.awb_no):
            lines.append(f"AWB: {row.awb_no}")
            lines.append(f"Reason: {row.ndr_reason}")
            lines.append(f"Diagnosis: {row.diagnosis_category}")
            lines.append(f"Risk: {row.risk_score}")
            lines.append(f"Recommendation: {row.recommended_action}")
            lines.append(f"Guidance: {row.manual_action_guidance}")
            lines.append(f"Reasoning: {row.reasoning}")
            lines.append("-" * 40)
            
        lines.append("")
        lines.append("NDR V1 provides recommendations for manual human execution.")
        lines.append("No autonomous mutation is performed against the ShopDeck main ecosystem.")
        
        self._create_binary_pdf(filepath, lines)
        return filepath
