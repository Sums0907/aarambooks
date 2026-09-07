from fastapi import APIRouter, Depends, Query
import asyncpg
from typing import Optional
from ..schemas.common import PaginatedResponse, PaginationMeta
from ..schemas.ndr import NDRShipmentContext, IntelligenceResult
from ..services.ndr import NDRService
from ..dependencies import get_ndr_service, get_db_pool
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/v1/ndr",
    tags=["NDR"]
)

@router.get("", response_model=PaginatedResponse[dict])
async def list_ndr(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    awb: Optional[str] = None,
    status: Optional[str] = None,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    offset = (page - 1) * limit
    
    where_clauses = []
    params = []
    
    if awb:
        params.append(f"%{awb}%")
        where_clauses.append(f"awb_no ILIKE ${len(params)}")
    if status:
        params.append(status)
        where_clauses.append(f"ndr_status = ${len(params)}")
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    query = f"""
        SELECT 
            awb_no, customer_name, courier_partner, 
            latest_ndr_reason, ndr_count, latest_ofd_time, ndr_status as status
        FROM shipment_ndr_reports
        {where_sql}
        ORDER BY latest_ndr_time DESC NULLS LAST
        LIMIT ${len(params)+1} OFFSET ${len(params)+2}
    """
    
    count_query = f"SELECT count(*) FROM shipment_ndr_reports {where_sql}"
    
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params)
        rows = await conn.fetch(query, *(params + [limit, offset]))
        
    return PaginatedResponse(
        data=[dict(r) for r in rows],
        meta=PaginationMeta(total=total, page=page, limit=limit)
    )

@router.get("/{awb_no}", response_model=NDRShipmentContext)
async def get_shipment_ndr(awb_no: str, service: NDRService = Depends(get_ndr_service)):
    return await service.get_shipment_ndr_context(awb_no)



@router.get("/reports/download/{report_id}/{artifact}", dependencies=[Depends(get_current_user)])
async def download_report(report_id: str, artifact: str):
    import os
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    
    allowed_extensions = {".csv", ".pdf"}
    if not any(artifact.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Invalid artifact extension")
    
    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "reports"))
    
    # Simple path traversal protection using basename
    filename = os.path.basename(artifact)
    if report_id not in filename:
        filename = f"{report_id}_{filename}"
        
    filepath = os.path.abspath(os.path.join(reports_dir, filename))
    if not filepath.startswith(reports_dir):
        raise HTTPException(status_code=400, detail="Invalid path")
        
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    return FileResponse(filepath, media_type="application/octet-stream", filename=filename)
