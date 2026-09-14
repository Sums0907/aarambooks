import asyncio
import logging
import uuid
from typing import Optional

from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter, ShopdeckQueueEvidenceMapper
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.intelligence_domains.ndr.communication_engine import CommunicationEngine
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.intelligence_domains.ndr.config import ndr_settings
from src.infrastructure.adapters.customer_engagement.models import EngagementState
class NDRQueuePoller:
    """
    Brain Queue Consumer.
    Polls ShopDeck BS for eligible NDR work, registers engagements, and dispatches calls.

    Supports concurrent dispatch orchestration bounded by max_concurrent_calls. This is a
    PROCESS-LOCAL asyncio.Semaphore, not a distributed lock - it bounds how many setup/dispatch
    pipelines (claim -> hydrate -> orchestrate -> register engagement -> Exotel dispatch ->
    correlation) run at once WITHIN THIS PROCESS. Running multiple Brain replicas each enforces
    its own local limit independently; ShopDeck BS's atomic claim_ndr_work is what prevents two
    replicas (or two local tasks) from ever processing the same queue item, not this semaphore.
    The slot is released as soon as the call is dispatched and the queue status is updated - it
    is never held for the live customer conversation, which is driven entirely by Exotel webhooks
    (src/api/webhooks/exotel_webhooks.py) on a separate path that this poller does not touch.
    """
    def __init__(
        self,
        shopdeck_adapter: ShopdeckCemAdapter,
        ccc_builder: CustomerConversationContextBuilder,
        comm_engine: CommunicationEngine,
        orchestrator: NDRIntelligenceOrchestrator,
        claimer_id: str = "brain_core_rabta",
        poll_interval_seconds: int = 15,
        lease_seconds: int = 300,
        max_concurrent_calls: int = 1,
    ):
        self.shopdeck_adapter = shopdeck_adapter
        self.ccc_builder = ccc_builder
        self.comm_engine = comm_engine
        self.orchestrator = orchestrator
        self.claimer_id = claimer_id
        self.poll_interval_seconds = poll_interval_seconds
        self.lease_seconds = lease_seconds
        self.max_concurrent_calls = max_concurrent_calls
        
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(self.max_concurrent_calls)
        self._active_tasks = set()

    def start(self):
        if not self._running:
            self._running = True
            self._loop_task = asyncio.create_task(self._poll_loop())
            logging.info(f"NDR Queue Poller started with claimer_id={self.claimer_id}, concurrency={self.max_concurrent_calls}")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
                
        # Await any remaining active dispatch tasks to ensure graceful shutdown
        if self._active_tasks:
            logging.info(f"NDR Queue Poller waiting for {len(self._active_tasks)} active tasks to complete...")
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
            
        logging.info("NDR Queue Poller stopped")

    async def _poll_loop(self):
        while self._running:
            try:
                # Calling-hours gate, checked BEFORE touching ShopDeck at all - not after
                # claiming. An NDR becoming eligible outside these hours must be left
                # completely untouched in ShopDeck's queue (not claimed, held, or rejected),
                # since claiming and then giving it back would burn into the limited
                # max_retries budget for no real reason. Real customers must never be called
                # outside this window regardless of when the underlying NDR occurred.
                if not ndr_settings.is_within_calling_hours():
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue

                # Acquire a concurrency slot before attempting to claim work
                await self._semaphore.acquire()

                # Check if we should stop while waiting for semaphore
                if not self._running:
                    self._semaphore.release()
                    break

                try:
                    item = await self.shopdeck_adapter.claim_ndr_work(self.claimer_id, self.lease_seconds)
                except Exception as claim_err:
                    logging.error(f"Error claiming NDR work: {claim_err}")
                    self._semaphore.release()
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue

                if not item:
                    # Queue is empty, release slot and sleep
                    self._semaphore.release()
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue

                # Spawn task to process the claimed item.
                # The task MUST release the semaphore in its finally block.
                task = asyncio.create_task(self._process_task_wrapper(item))
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)

            except Exception as e:
                logging.error(f"Error in NDR Queue Poller loop: {e}")
                await asyncio.sleep(self.poll_interval_seconds)

    async def _process_task_wrapper(self, item: dict):
        """
        Wraps the processing logic to guarantee semaphore release. Only this live-poll-loop
        path waits for the dispatched call to actually finish before releasing its dispatch
        slot (see _wait_for_call_completion) - process_next_item() deliberately does not, since
        it bypasses the semaphore entirely and is used by tests/certification scripts that
        don't simulate a webhook ever arriving.
        """
        try:
            engagement_id = await self._process_claimed_item(item)
            if engagement_id:
                await self._wait_for_call_completion(
                    engagement_id,
                    item.get("queue_item_id", "unknown"),
                    item.get("awb_no", "unknown"),
                )
        except Exception as e:
            logging.error(f"Unhandled exception in background dispatch task: {e}")
        finally:
            self._semaphore.release()

    async def process_next_item(self) -> bool:
        """
        Attempts to claim and process ONE item, awaiting full completion before returning.
        Bypasses the concurrency semaphore entirely - it is a single-shot path, not a
        second entry into the bounded pool. Used by tests that need synchronous
        claim-then-assert ordering, and by manual/certification scripts (execute_first_call.py,
        scripts/run_one_real_call.py, scripts/certify_gate2.py,
        scripts/certify_gate3_writeback.py) that construct their own NDRQueuePoller instance and
        never call start(), so there is no running _poll_loop for this to race with. Do not call
        this on a poller instance whose start() has been called from the same process, since that
        would run a dispatch pipeline outside the concurrency bound.
        """
        try:
            item = await self.shopdeck_adapter.claim_ndr_work(self.claimer_id, self.lease_seconds)
            if not item:
                return False
            await self._process_claimed_item(item)
            return True
        except Exception as e:
            logging.error(f"Error in synchronous process_next_item: {e}")
            return False

    async def _process_claimed_item(self, item: dict) -> Optional[str]:
        """
        Executes the full hydration, orchestration, and Exotel dispatch lifecycle
        for a single, already-claimed queue item. Returns the engagement_id if a call was
        actually dispatched, or None if it wasn't (no-action decision, already dispatched
        earlier, or a dispatch failure) - callers that need to wait for the live call to
        finish (see _process_task_wrapper) use this to know whether there is anything to wait
        for at all.
        """
        queue_item_id = item.get("queue_item_id", "unknown")
        awb_no = item.get("awb_no", "unknown")
        
        logging.info(f"Processing NDR queue item: {queue_item_id} for AWB: {awb_no}")

        engagement_id = None
        try:
            # If there's already an active engagement, do we reuse it?
            if item.get("current_engagement"):
                engagement_id = item["current_engagement"].get("engagement_id")
                call_sid = item["current_engagement"].get("call_sid")
                if call_sid:
                    # Already dispatched, just waiting for webhook. Do not dispatch again.
                    logging.info(f"[{queue_item_id} | {awb_no}] Already dispatched (call_sid={call_sid}). Skipping dispatch.")
                    return

            if not engagement_id:
                NAMESPACE_NDR = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
                engagement_id = f"eng_{uuid.uuid5(NAMESPACE_NDR, queue_item_id).hex}"

            # 3. Hydrate authoritative context & Consult Intelligence
            from src.shared.requirement_classification_contracts import ClassifiedRequirement
            from src.shared.conversational_contracts import ConversationalUnderstanding, SemanticEntityReference
            from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessRealityStatus

            # Fetch full evidence
            req = AbstractEvidenceRequest(
                classified_requirement=ClassifiedRequirement(
                    understanding=ConversationalUnderstanding(
                        original_query=f"Internal NDR Queue Fetch for AWB {awb_no}",
                        parameters=[],
                        entities=[SemanticEntityReference(inferred_type="ndr.entity.awb", original_expression=awb_no)]
                    )
                )
            )
            evidence_res = await self.shopdeck_adapter.execute_evidence_request(req)
            full_evidence = evidence_res.evidence_data if evidence_res.status == BusinessRealityStatus.EVIDENCE_AVAILABLE else {}

            # Map to EvidencePackage
            trigger_evidence = ShopdeckQueueEvidenceMapper.map_to_evidence(item, full_evidence)

            # Invoke true Intelligence Orchestrator
            decision = await self.orchestrator.orchestrate_resolution(trigger_evidence)

            if not decision.should_dispatch:
                logging.info(f"[{queue_item_id} | {awb_no} | {engagement_id}] NDR Orchestrator decided NO_ACTION (Disposition: {decision.disposition_code})")
                await self.shopdeck_adapter.update_queue_status(
                    queue_item_id=queue_item_id,
                    status="intelligence_no_action",
                    engagement_id=engagement_id,
                    failure_class=str(decision.disposition_code),
                    failure_reason=f"NDR intelligence disposition: {decision.disposition_code}",
                )
                return

            action = decision.action_request
            ccc = await self.ccc_builder.build(action)

            if not ccc.customer_profile.phone:
                raise ValueError(f"No authoritative customer phone hydrated for AWB {awb_no}; refusing to dispatch.")
            action.parameters["customer_phone"] = ccc.customer_profile.phone

            projection = self.ccc_builder.project(ccc)
            call_context = {**projection.model_dump(), "queue_item_id": queue_item_id}

            # 1. Brain local engagement creation
            engagement = await self.comm_engine.executor.prepare_engagement(
                action_request=action,
                engagement_id=engagement_id,
                call_context=call_context,
                ccc_snapshot=ccc.model_dump() if hasattr(ccc, "model_dump") else {}
            )
            logging.info(f"[{queue_item_id} | {awb_no} | {engagement_id}] Prepared Brain local engagement")

            # 2. ShopDeck BS engagement registration
            await self.shopdeck_adapter.register_engagement(
                queue_item_id=queue_item_id,
                engagement_id=engagement_id,
                idempotency_key=f"idem_{engagement_id}"
            )
            logging.info(f"[{queue_item_id} | {awb_no} | {engagement_id}] Registered engagement in ShopDeck BS")
            
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
            logging.info(f"[{queue_item_id} | {awb_no} | {engagement_id} | {call_sid}] Successfully dispatched call")
            return engagement_id

        except Exception as dispatch_err:
            logging.error(f"[{queue_item_id} | {awb_no}] Failed to dispatch call: {dispatch_err}")
            try:
                await self.shopdeck_adapter.update_queue_status(
                    queue_item_id=queue_item_id,
                    status="failed_retryable",
                    engagement_id=engagement_id,
                    failure_class="call_failed",
                    failure_reason=str(dispatch_err)
                )
            except Exception as update_err:
                logging.error(f"[{queue_item_id} | {awb_no}] Failed to record retryable state in ShopDeck: {update_err}")

    async def _wait_for_call_completion(self, engagement_id: str, queue_item_id: str, awb_no: str) -> None:
        """
        Blocks until the given engagement reaches a terminal state (COMPLETED, FAILED, or
        ESCALATED - set by the Exotel/Sarvam webhook handler when the live call truly ends),
        or until NDR_CALL_COMPLETION_MAX_WAIT_SECONDS elapses, whichever comes first. The
        caller (a task holding the dispatch semaphore) awaits this before returning, so the
        next queue item cannot be claimed until either the call finishes or this safety
        ceiling is hit.
        """
        terminal_states = {
            EngagementState.COMPLETED.value,
            EngagementState.FAILED.value,
            EngagementState.ESCALATED.value,
        }
        elapsed = 0
        while elapsed < ndr_settings.call_completion_max_wait_seconds:
            engagement = await self.comm_engine.executor.repository.get_engagement(engagement_id)
            status = engagement.get("status") if engagement else None
            if status in terminal_states:
                logging.info(f"[{queue_item_id} | {awb_no} | {engagement_id}] Call reached terminal state ({status}); dispatch slot free.")
                return
            await asyncio.sleep(ndr_settings.call_completion_poll_seconds)
            elapsed += ndr_settings.call_completion_poll_seconds

        logging.warning(
            f"[{queue_item_id} | {awb_no} | {engagement_id}] Call did not reach a terminal state within "
            f"{ndr_settings.call_completion_max_wait_seconds}s; freeing dispatch slot anyway to avoid "
            f"deadlocking the poller. This likely means the call's true outcome was never recorded "
            f"(e.g. a missed or dropped webhook) - worth checking this engagement manually."
        )
