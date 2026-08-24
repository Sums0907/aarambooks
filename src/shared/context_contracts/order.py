from pydantic import BaseModel
from typing import List, Dict, Any
from src.shared.context_contracts.source import SourceSystem, ContextSource

class OrderContext(BaseModel):
    order_reference: str
    source_system: SourceSystem
    status: str
    items: List[Dict[str, Any]] = []
    source: ContextSource
