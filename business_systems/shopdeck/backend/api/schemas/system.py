from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class SystemStatusResponse(BaseModel):
    status: str
    database_connected: bool
    version: str

class SyncHealthItem(BaseModel):
    table_name: str
    last_watermark: Optional[datetime]
    cadence_minutes: Optional[int]

class SyncHealthResponse(BaseModel):
    checkpoints: List[SyncHealthItem]
