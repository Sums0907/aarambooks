from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.shared.context_contracts.source import SourceSystem, ContextSource
from src.brain_core.models.contexts import CustomerContext, OrderContext, InventoryContext, ShipmentContext

class ContextAssemblyRequest(BaseModel):
    user_id: Optional[str] = None      
    customer_reference: Optional[str] = None  
    order_reference: Optional[str] = None     
    session_id: Optional[str] = None   
    source_system: Optional[SourceSystem] = None 

class SecurityContext(BaseModel):
    user_id: str
    roles: List[str] = []
    permissions: List[str] = []
    source: ContextSource

class IntelligenceContext(BaseModel):
    session_id: str
    recent_interactions: List[Dict[str, Any]] = []
    source: ContextSource

class AssembledContext(BaseModel):
    security: Optional[SecurityContext] = None
    customer: Optional[CustomerContext] = None
    order: Optional[OrderContext] = None
    inventory: Optional[InventoryContext] = None
    fulfillment: Optional[ShipmentContext] = None
    intelligence: Optional[IntelligenceContext] = None
    assembled_at: datetime
