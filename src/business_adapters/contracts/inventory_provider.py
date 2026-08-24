from typing import Protocol, Optional, List
from src.shared.context_contracts.inventory import InventoryContext

class InventoryContextProvider(Protocol):
    """
    Contract for retrieving Inventory Availability Context from AaramInventory.
    """
    async def get_inventory_context(self, item_references: List[str]) -> Optional[InventoryContext]:
        ...
