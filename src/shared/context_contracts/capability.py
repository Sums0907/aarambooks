from enum import Enum

class ProviderCapability(str, Enum):
    """
    Defines the standard capabilities that can be provided by Business Adapters.
    Owned by Shared Context Contracts to ensure Brain Core and Adapters share
    a common, neutral vocabulary without architectural coupling.
    """
    CUSTOMER = "customer"
    ORDER = "order"
    INVENTORY = "inventory"
    FULFILLMENT = "fulfillment"
    SECURITY = "security"
