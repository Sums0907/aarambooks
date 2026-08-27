from typing import Protocol, Optional
from src.shared.context_contracts.shipment import ShipmentContext

class ShipmentContextProvider(Protocol):
    """
    Contract for retrieving Shipment Context from an authoritative logistics/courier system.
    """
    async def get_shipment_context(self, shipment_reference: str) -> Optional[ShipmentContext]:
        ...
