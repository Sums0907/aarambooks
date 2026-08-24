from typing import Protocol, Optional
from src.shared.context_contracts.order import OrderContext

class OrderContextProvider(Protocol):
    """
    Contract for retrieving Order Context from an authoritative business system.
    The implementation adapter dictates the specific external system (e.g., ShopDeck).
    """
    async def get_order_context(self, order_reference: str) -> Optional[OrderContext]:
        ...
