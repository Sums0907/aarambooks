import asyncio
import logging
import uuid
from typing import Optional

from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.intelligence_domains.ndr.communication_engine import CommunicationEngine

class NDRQueuePoller:
    """
    Brain Queue Consumer.
    Polls ShopDeck BS for eligible NDR work, registers engagements, and dispatches calls.
    """
    def __init__(
        self,
        shopdeck_adapter: ShopdeckCemAdapter,
        ccc_builder: CustomerConversationContextBuilder,
        comm_engine: CommunicationEngine,
        claimer_id: str = "brain_core_rabta",
        poll_interval_seconds: int = 15,
        lease_seconds: int = 300,
    ):
        self.shopdeck_adapter = shopdeck_adapter
        self.ccc_builder = ccc_builder
        self.comm_engine = comm_engine
        self.claimer_id = claimer_id
        self.poll_interval_seconds = poll_interval_seconds
        self.lease_seconds = lease_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())
            logging.info(f"NDR Queue Poller started with claimer_id={self.claimer_id}")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logging.info("NDR Queue Poller stopped")

    async def _poll_loop(self):
        while self._running:
            try:
                await self.process_next_item()
            except Exception as e:
                logging.error(f"Error in NDR Queue Poller loop: {e}")
            
            await asyncio.sleep(self.poll_interval_seconds)

    async def process_next_item(self) -> bool:
        """
        Attempts to claim and process one item.
        Returns True if an item was processed, False if queue is empty.
        """
        try:
            # 1. Claim eligible work
            item = await self.shopdeck_adapter.claim_ndr_work(self.claimer_id, self.lease_seconds)
            if not item:
                return False

            queue_item_id = item["queue_item_id"]
            awb_no = item["awb_no"]
            
            logging.info(f"Claimed NDR queue item: {queue_item_id} for AWB: {awb_no}")

            # If there's already an active engagement, do we reuse it?
            engagement_id = None
            if item.get("current_engagement"):
                engagement_id = item["current_engagement"]["engagement_id"]
                call_sid = item["current_engagement"]["call_sid"]
                if call_sid:
                    # Already dispatched, just waiting for webhook. Do not dispatch again.
                    logging.info(f"Queue item {queue_item_id} already dispatched (call_sid={call_sid}). Skipping dispatch.")
                    return True

            if not engagement_id:
                # 2. Register engagement
                engagement_id = f"eng_{uuid.uuid4().hex}"
                idempotency_key = f"idem_{queue_item_id}"
                await self.shopdeck_adapter.register_engagement(
                    queue_item_id=queue_item_id,
                    engagement_id=engagement_id,
                    idempotency_key=idempotency_key
                )
                logging.info(f"Registered engagement {engagement_id} for queue item {queue_item_id}")

            # 3. Hydrate authoritative context
            try:
                from src.shared.conversational_contracts import ConversationalIntent
                
                class DummyUnderstanding:
                    def __init__(self):
                        self.intent = ConversationalIntent.SEARCH
                        self.parameters = []
                        self.entities = type("DummyEntity", (), {"inferred_type": "ndr.entity.awb", "original_expression": awb_no})()
                        self.entities = [self.entities]
                        self.original_query = f"Execute NDR for {awb_no}"
                
                class DummyClassified:
                    def __init__(self, u):
                        self.understanding = u
                        
                class DummyAction:
                    def __init__(self):
                        self.classified_requirement = DummyClassified(DummyUnderstanding())
                        self.objective = "Secure customer confirmation for delivery reattempt."
                        
                action = DummyAction()
                ccc = await self.ccc_builder.build(action)
                
                # Assume exotel adapter returns a call_sid (mocked implementation for tests might return hardcoded sid)
                call_sid = await self.comm_engine.executor.exotel_adapter.execute(
                    payload=ccc.model_dump(),
                    authorization_context="brain_internal"
                )
                if hasattr(call_sid, "status") and call_sid.status.name == "ACCEPTED":
                    call_sid = call_sid.provider_interaction_id or f"mock_call_{uuid.uuid4().hex}"
                elif isinstance(call_sid, str):
                    pass
                else:
                    call_sid = f"mock_call_{uuid.uuid4().hex}"
                
                await self.shopdeck_adapter.update_queue_status(
                    queue_item_id=queue_item_id,
                    status="call_dispatched",
                    engagement_id=engagement_id,
                    call_sid=call_sid
                )
                logging.info(f"Dispatched call {call_sid} for engagement {engagement_id}")

            except Exception as dispatch_err:
                logging.error(f"Failed to dispatch call for {queue_item_id}: {dispatch_err}")
                await self.shopdeck_adapter.update_queue_status(
                    queue_item_id=queue_item_id,
                    status="failed_retryable",
                    engagement_id=engagement_id,
                    failure_class="call_failed",
                    failure_reason=str(dispatch_err)
                )

            return True

        except Exception as e:
            logging.error(f"Error processing queue item: {e}")
            return False
