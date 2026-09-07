from fastapi import APIRouter, Depends, Query
import asyncpg
from typing import Optional
from ..schemas.common import PaginatedResponse, PaginationMeta
from ..dependencies import get_db_pool
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/v1/orders",
    tags=["Orders"],
    dependencies=[Depends(get_current_user)]
)

@router.get("", response_model=PaginatedResponse[dict], dependencies=[Depends(get_current_user)])
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order_id: Optional[str] = None,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    offset = (page - 1) * limit
    
    where_clauses = []
    params = []
    
    if order_id:
        params.append(f"%{order_id}%")
        where_clauses.append(f"(os.order_id ILIKE ${len(params)} OR os.order_id IN (SELECT order_id FROM order_line_items WHERE seller_group_id ILIKE ${len(params)}))")
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    query = f"""
        SELECT 
            os.order_id, 
            os.payment_mode, 
            os.total_amount, 
            os.payment_status, 
            os.updatedat, 
            os.createdat,
            (SELECT string_agg(DISTINCT seller_group_id, ', ') FROM order_line_items oli WHERE oli.order_id = os.order_id) as display_id
        FROM order_summary os
        {where_sql}
        ORDER BY os.updatedat DESC NULLS LAST
        LIMIT ${len(params)+1} OFFSET ${len(params)+2}
    """
    
    count_query = f"SELECT count(*) FROM order_summary os {where_sql}"
    
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params)
        rows = await conn.fetch(query, *(params + [limit, offset]))
        
    return PaginatedResponse(
        data=[dict(r) for r in rows],
        meta=PaginationMeta(total=total, page=page, limit=limit)
    )
