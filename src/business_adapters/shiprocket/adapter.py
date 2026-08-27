from typing import Optional
from datetime import datetime, timezone

from src.shared.context_contracts.source import SourceSystem, ContextSource
from src.shared.context_contracts.order import OrderContext
from src.shared.context_contracts.customer import CustomerContext
from src.shared.context_contracts.fulfillment import FulfillmentContext
from src.shared.context_contracts.shipment import ShipmentContext, DeliveryAttempt

from src.business_adapters.contracts.order_provider import OrderContextProvider
from src.business_adapters.contracts.customer_provider import CustomerContextProvider
from src.business_adapters.contracts.fulfillment_provider import FulfillmentContextProvider
from src.business_adapters.contracts.shipment_provider import ShipmentContextProvider

from .acquisition_client import ShiprocketAcquisitionClient

class ShiprocketAdapter(
    OrderContextProvider,
    CustomerContextProvider,
    FulfillmentContextProvider,
    ShipmentContextProvider
):
    """
    Shiprocket Adapter that translates raw synthetic Shiprocket payloads into semantic AaramBooks Contexts.
    It acts as an independent primary source for its own orders.
    """

    def __init__(self, client: ShiprocketAcquisitionClient):
        self.client = client
        
    def _create_source(self) -> ContextSource:
        return ContextSource(
            source_system_name=SourceSystem.shiprocket,
            retrieval_timestamp=datetime.now(timezone.utc)
        )

    async def get_order_context(self, order_reference: str) -> Optional[OrderContext]:
        order_details = await self.client.get_order_details(order_reference)
        if not order_details:
            return None
            
        items = []
        for item in order_details.get("products", []):
            items.append({
                "product_id": item.get("product_id"),
                "sku_id": item.get("sku"),
                "quantity": item.get("quantity"),
                "selling_price": item.get("price")
            })
            
        return OrderContext(
            order_reference=str(order_details["id"]),
            source_system=SourceSystem.shiprocket,
            status=order_details.get("status", "Unknown"),
            items=items,
            source=self._create_source()
        )

    async def get_customer_context(self, customer_reference: str) -> Optional[CustomerContext]:
        # For Shiprocket, customer_reference is mapped to the order_id 
        # since customer details are embedded in the order payload.
        order_details = await self.client.get_order_details(customer_reference)
        if not order_details:
            return None
            
        return CustomerContext(
            customer_reference=None, # Shiprocket provides no discrete customer ID
            source_system=SourceSystem.shiprocket,
            name=order_details.get("customer_name"),
            phone_number=order_details.get("customer_phone"),
            source=self._create_source()
        )

    async def get_fulfillment_context(self, order_reference: str) -> Optional[FulfillmentContext]:
        order_details = await self.client.get_order_details(order_reference)
        if not order_details:
            return None
            
        return FulfillmentContext(
            fulfillment_status=order_details.get("status"),
            source=self._create_source()
        )

    async def get_shipment_context(self, shipment_reference: str) -> Optional[ShipmentContext]:
        tracking = await self.client.get_shipment_tracking(shipment_reference)
        if not tracking:
            return None
            
        shipment_track = tracking.get("shipment_track", [{}])
        track_info = shipment_track[0] if shipment_track else {}
        
        raw_activities = tracking.get("shipment_track_activities", [])
        
        delivery_attempts = []
        raw_events_preserved = []
        
        for event in raw_activities:
            sr_status = event.get("sr-status")
            
            # Strict inference rule: DO NOT label as attempt unless explicitly known.
            # INFERRED: sr-status 17 and 19 are known to represent 'Out for Delivery' or similar attempts based on official docs.
            # If not in the explicitly known list, we preserve the raw event.
            is_attempt = sr_status in [17, 19]
            
            if is_attempt:
                try:
                    dt = datetime.strptime(event["date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) # Documented format without Z
                except (ValueError, TypeError, KeyError):
                    dt = datetime.now(timezone.utc)
                
                delivery_attempts.append(DeliveryAttempt(
                    attempt_timestamp=dt,
                    status=event.get("activity", "Unknown"),
                    reason=None, # Reason is usually bundled in activity string in live API
                    remarks=event.get("location")
                ))
            else:
                raw_events_preserved.append(event)
                
        return ShipmentContext(
            shipment_reference=str(track_info.get("awb_code", shipment_reference)),
            source_system=SourceSystem.shiprocket,
            awb_no=str(track_info.get("awb_code", shipment_reference)),
            courier=track_info.get("courier_name", "Unknown"),
            status=track_info.get("current_status", "Unknown"),
            delivery_attempts=delivery_attempts,
            raw_tracking_events=raw_events_preserved,
            source=self._create_source()
        )
