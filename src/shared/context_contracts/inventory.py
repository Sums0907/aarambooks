from pydantic import BaseModel
from typing import Dict
from src.shared.context_contracts.source import ContextSource

class InventoryContext(BaseModel):
    items_availability: Dict[str, bool] = {}
    source: ContextSource
