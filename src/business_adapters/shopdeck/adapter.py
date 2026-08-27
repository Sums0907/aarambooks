from typing import Optional, List
from datetime import datetime, timezone

from src.shared.context_contracts.source import SourceSystem, ContextSource
from src.shared.context_contracts.order import OrderContext
from src.shared.context_contracts.customer import CustomerContext
from src.shared.context_contracts.fulfillment import FulfillmentContext

from src.business_adapters.contracts.order_provider import OrderContextProvider
from src.business_adapters.contracts.customer_provider import CustomerContextProvider
from src.business_adapters.contracts.fulfillment_provider import FulfillmentContextProvider

from .acquisition_client import ShopDeckAcquisitionClient

class ShopDeckAdapter(
    OrderContextProvider,
    CustomerContextProvider,
    FulfillmentContextProvider
):
    """
    ShopDeck Adapter that translates raw ShopDeck records into semantic AaramBooks Contexts.
    It isolates the transport mechanism behind the ShopDeckAcquisitionClient.
    """

    def __init__(self, client: ShopDeckAcquisitionClient):
        self.client = client
        
    def _create_source(self) -> ContextSource:
        return ContextSource(
            source_system_name=SourceSystem.shopdeck,
            retrieval_timestamp=datetime.now(timezone.utc)
        )

    async def get_order_context(self, order_reference: str) -> Optional[OrderContext]:
        order_summary = await self.client.get_order_summary(order_reference)
        if not order_summary:
            return None
            
        line_items = await self.client.get_order_line_items(order_reference)
        
        # Determine overall payment status string
        payment_status = "Paid" if order_summary.get("payment_status") else "Pending"
        
        items = []
        for li in line_items:
            # sku_id is known to be NULL in ShopDeck currently, but we preserve the field explicitly
            sku_id = li.get("sku_id")
            items.append({
                "seller_group_id": li.get("seller_group_id"),
                "sku_id": sku_id,
                "quantity": li.get("quantity"),
                "awb_no": li.get("awb_no"),
                "selling_price": li.get("selling_price"),
                "seller_last_status": li.get("seller_last_status"),
                "cancellation_reason_code": li.get("cancellation_reason_code")
            })
            
        return OrderContext(
            order_reference=str(order_summary["order_id"]),
            source_system=SourceSystem.shopdeck,
            status=payment_status,
            items=items,
            source=self._create_source()
        )

    async def get_customer_context(self, customer_reference: str) -> Optional[CustomerContext]:
        customer_info = await self.client.get_customer_info_by_id(customer_reference)
        if not customer_info:
            return None
            
        return CustomerContext(
            customer_reference=str(customer_info["customer_id"]),
            source_system=SourceSystem.shopdeck,
            name=customer_info.get("customer_name"), # may come from order_line_items, but we map if present
            phone_number=None, # Encrypted in ShopDeck, cannot be used natively
            source=self._create_source()
        )

    async def get_fulfillment_context(self, order_reference: str) -> Optional[FulfillmentContext]:
        line_items = await self.client.get_order_line_items(order_reference)
        if not line_items:
            return None
            
        # If there are multiple items, we take a summary status. 
        # For this foundation, we just take the first item's seller_last_status.
        status = line_items[0].get("seller_last_status") if line_items else None
        
        return FulfillmentContext(
            fulfillment_status=status,
            source=self._create_source()
        )
