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
                NAMESPACE_NDR = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
                engagement_id = f"eng_{uuid.uuid5(NAMESPACE_NDR, queue_item_id).hex}"

            # 3. Hydrate authoritative context
            try:
                from src.shared.conversational_contracts import ConversationalIntent
                from src.intelligence_domains.ndr.mission_factory import build_ndr_mission

                # Mission is derived from the claimed queue item, NOT from CCC hydration.
                # It is an INPUT to ccc_builder.build() (the directive is a required argument),
                # so it must exist before the CCC does. Sourcing it from hydrated evidence such
                # as ndr_count would be circular.
                mission = build_ndr_mission(item)
                
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
                    def __init__(self, qid, mission):
                        self.classified_requirement = DummyClassified(DummyUnderstanding())
                        # customer_phone starts unset. It is NOT dead: exotel_adapter.dispatch_call
                        # reads action_request.parameters["customer_phone"] as the literal "From"
                        # number on the real outbound call (src/infrastructure/adapters/
                        # customer_engagement/exotel_adapter.py:37). It is filled in below, after
                        # ccc_builder.build() hydrates the authoritative phone from ShopDeck, and
                        # dispatch is refused if hydration could not produce one.
                        self.parameters = {"awb_no": awb_no}
                        # Use deterministic action_request_id so idempotency matches on retry
                        NAMESPACE_NDR = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
                        self.action_request_id = f"act_{uuid.uuid5(NAMESPACE_NDR, qid).hex}"
                        from src.brain_core.action_engine.contracts import ConversationalDirective
                        self.directive = ConversationalDirective(
                            objective=mission.primary_objective,
                            context_summary=mission.why_this_call,
                            allowed_actions=mission.allowed_actions,
                            constraints=[
                                "Never state a fact that is not present in the authoritative context.",
                                "Never pressure the customer into a delivery date.",
                                "Never abandon the delivery topic, and never ask a generic 'anything else?'.",
                            ],
                            mission=mission,
                        )
                        from src.brain_core.action_engine.contracts import ExecutionIntent, ExecutionChannel
                        self.execution_intent = ExecutionIntent(intent_type="ndr_outbound", channel=ExecutionChannel.VOICE)
                        
                action = DummyAction(queue_item_id, mission)
                ccc = await self.ccc_builder.build(action)

                # Authoritative phone, from ShopDeck via CCC hydration - never a placeholder.
                # ccc_builder.build() already raises if ShopDeck provided no phone at all, so
                # this is a belt-and-suspenders check against a future hydration change that
                # makes the field optional without the caller (here) noticing.
                if not ccc.customer_profile.phone:
                    raise ValueError(f"No authoritative customer phone hydrated for AWB {awb_no}; refusing to dispatch.")
                action.parameters["customer_phone"] = ccc.customer_profile.phone
                
                # 1. Brain local engagement creation
                engagement = await self.comm_engine.executor.prepare_engagement(
                    action_request=action,
                    engagement_id=engagement_id,
                    # queue_item_id is stored here because CustomerEngagementRecord has no
                    # metadata field - the transcript webhook's NDR intelligence writeback
                    # needs it to identify which ndr_queue row to update, and this is the only
                    # place it's available before ShopDeck's own claim-status flow discards it.
                    call_context={"awb_no": awb_no, "customer_phone": ccc.customer_profile.phone, "queue_item_id": queue_item_id},
                    ccc_snapshot=ccc.model_dump() if hasattr(ccc, "model_dump") else {}
                )
                logging.info(f"Prepared Brain local engagement {engagement_id}")

                # 2. ShopDeck BS engagement registration
                await self.shopdeck_adapter.register_engagement(
                    queue_item_id=queue_item_id,
                    engagement_id=engagement_id,
                    idempotency_key=f"idem_{engagement_id}"
                )
                logging.info(f"Registered engagement {engagement_id} for queue item {queue_item_id}")
                
                # 3. Exotel Dispatch
                dispatch_result = await self.comm_engine.executor.dispatch_provider_call(engagement, action)
                call_sid = dispatch_result.get("provider_interaction_id") or dispatch_result.get("call_id") or f"mock_call_{uuid.uuid4().hex}"
                if hasattr(call_sid, "status") and call_sid.status.name == "ACCEPTED":
                    call_sid = call_sid.provider_interaction_id or f"mock_call_{uuid.uuid4().hex}"
                elif isinstance(call_sid, str):
                    pass
                else:
                    call_sid = f"mock_call_{uuid.uuid4().hex}"
                
                # 4. Persist provider correlation
                await self.comm_engine.executor.persist_provider_correlation(engagement_id, call_sid)
                
                # 5. ShopDeck queue call_dispatched
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
