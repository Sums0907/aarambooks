from typing import Protocol, Optional
from src.shared.context_contracts.customer import CustomerContext

class CustomerContextProvider(Protocol):
    """
    Contract for retrieving Customer Context from an authoritative business system.
    The implementation adapter dictates the specific external system (e.g., ShopDeck).
    """
    async def get_customer_context(self, customer_reference: str) -> Optional[CustomerContext]:
        ...
