from typing import Protocol, Optional, Dict, Any, List

class ShiprocketAcquisitionClient(Protocol):
    """
    Protocol defining the acquisition boundary for Shiprocket data.
    This interface abstracts away the underlying Shiprocket API.
    """
    
    async def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the order and fulfillment details for an order."""
        ...
        
    async def get_shipment_tracking(self, awb_no: str) -> Optional[Dict[str, Any]]:
        """Fetch the shipment tracking and NDR history for an AWB."""
        ...
