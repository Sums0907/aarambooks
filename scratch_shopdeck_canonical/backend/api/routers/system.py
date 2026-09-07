from fastapi import APIRouter, Depends
import asyncpg
from ..schemas.system import SystemStatusResponse, SyncHealthResponse, SyncHealthItem
from ..dependencies import get_db_pool
from ..auth import get_current_user
from shopdeck.config import CADENCE_MINUTES # We can import from config for cadence info

router = APIRouter(
    prefix="/api/v1",
    tags=["System"]
)

@router.get("/system/status", response_model=SystemStatusResponse)
async def system_status(pool: asyncpg.Pool = Depends(get_db_pool)):
    db_connected = False
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        db_connected = True
    except Exception:
        pass

    return SystemStatusResponse(
        status="ok" if db_connected else "degraded",
        database_connected=db_connected,
        version="1.0.0"
    )

@router.get("/sync/health", response_model=SyncHealthResponse, dependencies=[Depends(get_current_user)])
async def sync_health(pool: asyncpg.Pool = Depends(get_db_pool)):
    checkpoints = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT table_name, last_watermark FROM sync_checkpoints")
            for r in rows:
                t_name = r["table_name"]
                # Proxy checkpoints don't have direct cadences, fallback to generic
                cadence = CADENCE_MINUTES.get(t_name) if t_name in CADENCE_MINUTES else (
                    CADENCE_MINUTES.get("ndr_proxy") if "proxy" in t_name else None
                )
                checkpoints.append(SyncHealthItem(
                    table_name=t_name,
                    last_watermark=r["last_watermark"],
                    cadence_minutes=cadence
                ))
    except Exception:
        pass
    
    return SyncHealthResponse(checkpoints=checkpoints)
