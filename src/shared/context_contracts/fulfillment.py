from pydantic import BaseModel
from typing import Optional
from src.shared.context_contracts.source import ContextSource

class FulfillmentContext(BaseModel):
    fulfillment_status: Optional[str] = None
    source: ContextSource
