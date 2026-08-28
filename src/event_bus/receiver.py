import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from src.security.validator import PayloadValidator, SecurityValidationError
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.event_bus.dispatcher import OutboundDispatcher
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata
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
        except Exception as e:
            logging.error(f"Routing failed: {e}")
            raise
            
        return None

    def _create_evidence_package(self, event_type: str, content: Dict[str, Any]) -> EvidencePackage:
        item = EvidenceItem(
            item_id=str(uuid.uuid4()),
            semantic_identity=event_type,
            data_payload=content,
            provenance=ProvenanceMetadata(
                retrieval_timestamp=datetime.now(timezone.utc),
                derivation_metadata="event_bus_webhook"
            )
        )
        return EvidencePackage(
            package_id=str(uuid.uuid4()),
            plan_id="event_trigger",
            evidence_items=[item],
            sufficiency_assessment="SUFFICIENT"
        )

    async def _route_customer_query(self, content: Dict[str, Any]) -> Optional[str]:
        package = self._create_evidence_package("customer_query", content)
        
        _, _, action = await self.query_orchestrator.handle_query(trigger_evidence=package)
        
        if action:
            return OutboundDispatcher.dispatch(action)
        return None

    async def _route_ndr(self, content: Dict[str, Any]) -> Optional[str]:
        package = self._create_evidence_package("ndr_update", content)
        
        _, action, _ = await self.ndr_orchestrator.orchestrate_resolution(trigger_evidence=package)
        
        if action:
            return OutboundDispatcher.dispatch(action)
        return None
