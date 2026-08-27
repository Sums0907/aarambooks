from typing import Protocol, Optional, Dict, Any, List

class ShopDeckAcquisitionClient(Protocol):
    """
    Protocol defining the acquisition boundary for ShopDeck data.
    This interface abstracts away the underlying transport mechanism
    (e.g., custom MCP, future S2S API, or mock fixtures).
    """
    
    async def get_order_summary(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the order_summary row for an order."""
        ...
        
    async def get_order_line_items(self, order_id: str) -> List[Dict[str, Any]]:
        """Fetch all order_line_items for an order."""
        ...
        
    async def get_customer_info(self, awb_no: str) -> Optional[Dict[str, Any]]:
        """Fetch the customer_info row for an AWB."""
        ...

    async def get_customer_info_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the customer_info row by customer_id."""
        ...
        
    async def get_shipment_ndr_report(self, awb_no: str) -> Optional[Dict[str, Any]]:
        """Fetch the current shipment_ndr_reports row for an AWB."""
        ...
        
    async def get_ndr_action_log(self, awb_no: str) -> List[Dict[str, Any]]:
        """Fetch the historical ndr_action_log rows for an AWB."""
        ...
