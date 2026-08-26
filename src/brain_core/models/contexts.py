from pydantic import BaseModel, ConfigDict, Field
from typing import List

class FrozenContextModel(BaseModel):
    """Base model for all contexts to enforce immutability and prevent extra fields."""
    model_config = ConfigDict(frozen=True, extra='forbid')

class CustomerContext(FrozenContextModel):
    """
    Intelligence view of a customer.
    Fields derived directly from docs/04-data-models/customer-context-model.md
    """
    customer_id: str
    interactions: List[str] = Field(default_factory=list)
    needs: List[str] = Field(default_factory=list)
    previous_conversations: List[str] = Field(default_factory=list)
    resolution_history: List[str] = Field(default_factory=list)
    relevant_business_situations: List[str] = Field(default_factory=list)

class OrderContext(FrozenContextModel):
    """Minimal representation of an order until a concrete API fixture is provided."""
    order_id: str

class ShipmentContext(FrozenContextModel):
    """Minimal representation of a shipment until a concrete API fixture is provided."""
    shipment_id: str

class InventoryContext(FrozenContextModel):
    """Minimal representation of inventory until a concrete API fixture is provided."""
    item_id: str
    quantity_on_hand: float = 0.0
