import logging
from typing import Dict, Any, Optional
from src.security.validator import PayloadValidator, SecurityValidationError
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.brain_core.models.contexts import CustomerContext, OrderContext, ShipmentContext
from src.event_bus.dispatcher import OutboundDispatcher
from pydantic import ValidationError

class InboundReceiver:
    def __init__(self, query_orchestrator: CustomerQueryOrchestrator, ndr_orchestrator: NDRIntelligenceOrchestrator):
        self.query_orchestrator = query_orchestrator
        self.ndr_orchestrator = ndr_orchestrator
        
    async def process_raw_payload(self, raw_payload: str) -> Optional[str]:
        """
        1. Validate payload.
        2. Route to domain.
        3. Dispatch output.
        Returns the dispatched JSON string or None if no action.
        """
        try:
            safe_payload = PayloadValidator.validate_inbound_event(raw_payload)
        except SecurityValidationError as e:
            logging.error(f"Security validation failed: {e}")
            raise
            
        event_type = safe_payload["event_type"]
        content = safe_payload["content"]
        
        try:
            if event_type == "customer_query":
                return await self._route_customer_query(content)
            elif event_type == "ndr_update":
                return await self._route_ndr(content)
        except ValidationError as e:
            raise SecurityValidationError(f"Invalid domain structure in content: {e}")
        except Exception as e:
            logging.error(f"Routing failed: {e}")
            raise
            
        return None

    async def _route_customer_query(self, content: Dict[str, Any]) -> Optional[str]:
        query_text = content.get("query_text", "")
        customer_dict = content.get("customer_context", {})
        order_dict = content.get("order_context")
        session_id = content.get("session_id")
        
        customer_context = CustomerContext.model_validate(customer_dict)
        order_context = OrderContext.model_validate(order_dict) if order_dict else None
        
        _, _, action = await self.query_orchestrator.handle_query(
            query_text=query_text,
            customer_context=customer_context,
            order_context=order_context,
            session_id=session_id
        )
        
        if action:
            return OutboundDispatcher.dispatch(action)
        return None

    async def _route_ndr(self, content: Dict[str, Any]) -> Optional[str]:
        shipment_dict = content.get("shipment_context", {})
        customer_dict = content.get("customer_context", {})
        order_dict = content.get("order_context")
        
        shipment_context = ShipmentContext.model_validate(shipment_dict)
        customer_context = CustomerContext.model_validate(customer_dict)
        order_context = OrderContext.model_validate(order_dict) if order_dict else None
        
        _, action, _ = await self.ndr_orchestrator.orchestrate_resolution(
            shipment_context=shipment_context,
            customer_context=customer_context,
            order_context=order_context
        )
        
        if action:
            return OutboundDispatcher.dispatch(action)
        return None
