from fastapi import APIRouter, Depends, Query
import asyncpg
from typing import Optional
from ..schemas.common import PaginatedResponse, PaginationMeta
from ..dependencies import get_db_pool
from ..auth import get_current_user

router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Customers"],
    dependencies=[Depends(get_current_user)]
)

@router.get("", response_model=PaginatedResponse[dict], dependencies=[Depends(get_current_user)])
async def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    customer_id: Optional[str] = None,
    phone: Optional[str] = None,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    offset = (page - 1) * limit
    
    where_clauses = []
    params = []
    
    if customer_id:
        params.append(f"%{customer_id}%")
        where_clauses.append(f"customer_id ILIKE ${len(params)}")
    if phone:
        # Note: schema indicates customer_number is encrypted. 
        # But we support exact matching if it's the exact ciphertext or we just allow it to run and return empty if mismatched.
        params.append(phone)
        where_clauses.append(f"customer_number = ${len(params)}")
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    query = f"""
        SELECT 
            ci.customer_id, 
            ci.awb_no, 
            ci.pickup_city, 
            ci.pickup_state, 
            ci.drop_city, 
            ci.drop_state, 
            ci.updatedat,
            (SELECT customer_name FROM order_line_items oli WHERE oli.customer_id = ci.customer_id AND customer_name IS NOT NULL LIMIT 1) as customer_name
        FROM customer_info ci
        {where_sql.replace('customer_id', 'ci.customer_id').replace('customer_number', 'ci.customer_number')}
        ORDER BY ci.updatedat DESC NULLS LAST
        LIMIT ${len(params)+1} OFFSET ${len(params)+2}
    """
    
    count_query = f"SELECT count(*) FROM customer_info {where_sql}"
    
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params)
        rows = await conn.fetch(query, *(params + [limit, offset]))
        
    return PaginatedResponse(
        data=[dict(r) for r in rows],
        meta=PaginationMeta(total=total, page=page, limit=limit)
    )
