from fastapi import APIRouter, Depends, Query, HTTPException
import asyncpg
from typing import Optional
from datetime import datetime
from ..schemas.common import PaginatedResponse, PaginationMeta
from ..dependencies import get_db_pool
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/v1/events",
    tags=["Events"],
    dependencies=[Depends(get_current_user)]
)

ALLOWED_TABLES = {
    "cancel_reason_events",
    "order_cancellation_events",
    "return_exchange_events",
    "post_order_survey_submit_events",
    "rating_review_feedback_submit_events",
    "payment_gateway_events",
    "checkout_external_events",
    "checkout_input_error_events"
}

@router.get("/{table_name}", response_model=PaginatedResponse[dict], dependencies=[Depends(get_current_user)])
async def list_events(
    table_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid event table")

    offset = (page - 1) * limit
    
    where_clauses = []
    params = []
    
    if start_date:
        params.append(start_date)
        where_clauses.append(f"created_at >= ${len(params)}")
    if end_date:
        params.append(end_date)
        where_clauses.append(f"created_at <= ${len(params)}")
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    # Selecting all columns for events since they vary wildly and UI shows generic detail
    query = f"""
        SELECT *
        FROM "{table_name}"
        {where_sql}
        ORDER BY created_at DESC NULLS LAST
        LIMIT ${len(params)+1} OFFSET ${len(params)+2}
    """
    
    count_query = f'SELECT count(*) FROM "{table_name}" {where_sql}'
    
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params)
        rows = await conn.fetch(query, *(params + [limit, offset]))
        
    return PaginatedResponse(
        data=[dict(r) for r in rows],
        meta=PaginationMeta(total=total, page=page, limit=limit)
    )
