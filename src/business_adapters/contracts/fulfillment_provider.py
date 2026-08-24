from typing import Protocol, Optional
from src.shared.context_contracts.fulfillment import FulfillmentContext

class FulfillmentContextProvider(Protocol):
    """
    Contract for retrieving Fulfillment Status Context from AaramPacking.
    """
    async def get_fulfillment_context(self, order_reference: str) -> Optional[FulfillmentContext]:
        ...
