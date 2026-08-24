from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SourceSystem(str, Enum):
    aaram_identity = "aaram_identity"
    shopdeck = "shopdeck"
    amazon = "amazon"
    flipkart = "flipkart"
    aaram_inventory = "aaram_inventory"
    aaram_packing = "aaram_packing"
    memory_framework = "memory_framework"

class ContextAssemblyRequest(BaseModel):
    user_id: Optional[str] = None      # For Security Context
    customer_reference: Optional[str] = None  # For Customer Context
    order_reference: Optional[str] = None     # For Order Context
    session_id: Optional[str] = None   # For Intelligence Context
    source_system: Optional[SourceSystem] = None # Hint for routing to the correct business adapter

class ContextSource(BaseModel):
    source_system_name: SourceSystem
    retrieval_timestamp: datetime

class SecurityContext(BaseModel):
    # strictly authentication and authorization from AaramIdentity
    user_id: str
    roles: List[str] = []
    permissions: List[str] = []
    source: ContextSource

class CustomerContext(BaseModel):
    # strictly customer context snapshot retrieved from authoritative business systems.
    customer_reference: str
    source_system: SourceSystem
    name: Optional[str] = None
    phone_number: Optional[str] = None
    source: ContextSource

class OrderContext(BaseModel):
    # strictly order context snapshot retrieved from authoritative business systems.
    order_reference: str
    source_system: SourceSystem
    status: str
    items: List[Dict[str, Any]] = []
    source: ContextSource

class InventoryContext(BaseModel):
    # strictly from AaramInventory
    items_availability: Dict[str, bool] = {}
    source: ContextSource

class FulfillmentContext(BaseModel):
    # strictly from AaramPacking
    fulfillment_status: Optional[str] = None
    source: ContextSource

class IntelligenceContext(BaseModel):
    # strictly from Brain Memory Framework
    session_id: str
    recent_interactions: List[Dict[str, Any]] = []
    source: ContextSource

class AssembledContext(BaseModel):
    security: Optional[SecurityContext] = None
    customer: Optional[CustomerContext] = None
    order: Optional[OrderContext] = None
    inventory: Optional[InventoryContext] = None
    fulfillment: Optional[FulfillmentContext] = None
    intelligence: Optional[IntelligenceContext] = None
    assembled_at: datetime
