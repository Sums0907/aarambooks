from pydantic import BaseModel
from typing import Optional
from src.shared.context_contracts.source import SourceSystem, ContextSource

class CustomerContext(BaseModel):
    customer_reference: str
    source_system: SourceSystem
    name: Optional[str] = None
    phone_number: Optional[str] = None
    source: ContextSource
