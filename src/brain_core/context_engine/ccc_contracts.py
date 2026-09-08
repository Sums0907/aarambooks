from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from src.brain_core.action_engine.contracts import ConversationalDirective

class CustomerContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    name: Optional[str] = None
    phone: str

class OrderContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    awb_no: str
    collectable_amount: float
    payment_mode: str
    actual_item_price: Optional[float] = None
    order_quantity: Optional[int] = None
    courier_partner: Optional[str] = None
    past_delivery_attempts: Optional[int] = None

class ProductContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    sku_id: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    catalog_selling_price: Optional[float] = None
    mrp: Optional[float] = None
    image_url: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    features: Optional[str] = None
    return_exchange_condition: Optional[str] = None
    attr_style: Optional[str] = None
    attr_pattern: Optional[str] = None
    attr_package_contents: Optional[str] = None
    rich_attributes_available: bool = False

class CustomerConversationContext(BaseModel):
    """Immutable call-scoped authoritative snapshot."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    ccc_id: str
    target_identity: str
    
    customer_profile: CustomerContext
    order_facts: OrderContext
    product_context: ProductContext
    
    directive: ConversationalDirective

class CustomerConversationProjection(BaseModel):
    """Governed, filtered subset permitted to reach SUNEHRI LLM."""
    model_config = ConfigDict(frozen=True, extra='forbid')
    
    customer_name: Optional[str] = None
    customer_phone: str
    awb_no: str
    collectable_amount: float
    payment_mode: str
    actual_item_price: Optional[float] = None
    order_quantity: Optional[int] = None
    courier_partner: Optional[str] = None
    past_delivery_attempts: Optional[int] = None
    
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_code: Optional[str] = None
    sku_id: Optional[str] = None
    catalog_selling_price: Optional[float] = None
    mrp: Optional[float] = None
    image_url: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    features: Optional[str] = None
    return_exchange_condition: Optional[str] = None
    attr_style: Optional[str] = None
    attr_pattern: Optional[str] = None
    attr_package_contents: Optional[str] = None
    
    objective: str
    context_summary: str
    domain_constraints: List[str]
    core_safety_constraints: List[str]
    allowed_actions: List[str]

    # Mission, flattened to scalars on purpose.
    # The Exotel session_constants payload is a flat string->string map and str()s whatever it
    # is handed, so a nested dict here would reach the LLM as a Python-repr blob. Every field
    # below must also be added to the allow-list loop in src/api/webhooks/exotel_webhooks.py
    # or it will silently never reach the call.
    mission_conversation_mission: Optional[str] = None
    mission_why_this_call: Optional[str] = None
    mission_primary_objective: Optional[str] = None
    mission_success_condition: Optional[str] = None
    mission_initial_state: Optional[str] = None
    mission_allowed_next_states: Optional[str] = None
    mission_conversation_priority: Optional[str] = None
    mission_return_to_mission: Optional[str] = None
