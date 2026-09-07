import uuid
import os
import json
from datetime import datetime, UTC
from typing import Optional, List
from src.infrastructure.mongo_client import get_mongo_db
from .projection import NDRReportProjection
from .generator import NDRReportGenerator

class NDRReportService:
    """Service to coordinate deterministic NDR report generation."""
    
    def __init__(self, output_dir: str = "/tmp/reports"):
        self.output_dir = output_dir
        self.generator = NDRReportGenerator(output_dir)
        
    async def generate_report(self, window_start: datetime, window_end: datetime) -> dict:
        """
        Generates a deterministic NDR Action Report based on a time window.
        Idempotent: Identical inputs produce identical semantics.
        """
        db = await get_mongo_db()
        
        # ELIGIBILITY RULE: Normalization COMPLETED and action != NONE
        cursor = db.ndr_normalization_results.find({
            "normalization_status": "COMPLETED",
            "authorized_action": {"$ne": "NONE"},
            "completed_at": {"$gte": window_start, "$lte": window_end}
        }).sort("awb_no", 1) # Ensure stable ordering from DB where possible
        
        results = await cursor.to_list(length=1000)
        
        if not results:
            return {"status": "no_eligible_records"}
            
        # Create deterministic report_id based on window
        report_id = f"ndr_report_{window_start.strftime('%Y%m%d%H%M')}_{window_end.strftime('%Y%m%d%H%M')}"
        reporting_period = f"{window_start.isoformat()} to {window_end.isoformat()}"
        
        # PROJECTION
        rows = [NDRReportProjection.project(r) for r in results]
        
        # GENERATION
        csv_path = self.generator.generate_csv(report_id, rows)
        pdf_path = self.generator.generate_pdf(report_id, reporting_period, rows)
        
        metadata = {
            "report_id": report_id,
            "report_version": "1.0",
            "reporting_window": reporting_period,
            "generated_at": datetime.now(UTC).isoformat(),
            "record_count": len(rows),
            "csv_path": csv_path,
            "pdf_path": pdf_path
        }
        
        # Log metadata idempotently (could be saved to DB, here just returning)
        return metadata
