import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.workers.ndr_queue_poller import NDRQueuePoller

class MockShopdeckAdapter(AsyncMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = []
        self.claim_delays = []
        
    async def claim_ndr_work(self, claimer_id, lease_seconds):
        if self.claim_delays:
            await asyncio.sleep(self.claim_delays.pop(0))
        if self.queue:
            return self.queue.pop(0)
        return None

    async def update_queue_status(self, *args, **kwargs):
        pass

class FakeCCCBuilder:
    async def build(self, action):
        mock_ccc = MagicMock()
        mock_ccc.customer_profile.phone = "9999999999"
        return mock_ccc
        
    def project(self, ccc):
        proj = MagicMock()
        proj.model_dump.return_value = {"projected": "yes"}
        return proj

class FakeOrchestrator:
    async def orchestrate_resolution(self, evidence):
        decision = MagicMock()
        decision.should_dispatch = True
        decision.action_request.parameters = {}
        return decision

class FakeExecutor:
    def __init__(self):
        self.active_dispatches = 0
        self.max_concurrent_observed = 0
        self.dispatch_calls = []

    async def prepare_engagement(self, action_request, engagement_id, call_context, ccc_snapshot):
        return {"eng_id": engagement_id}

    async def dispatch_provider_call(self, engagement, action):
        self.active_dispatches += 1
        if self.active_dispatches > self.max_concurrent_observed:
            self.max_concurrent_observed = self.active_dispatches
            
        self.dispatch_calls.append(engagement["eng_id"])
        
        # Simulate blocking time to force concurrency overlap
        await asyncio.sleep(0.1)
        
        self.active_dispatches -= 1
        return {"provider_interaction_id": "sid_123"}

    async def persist_provider_correlation(self, eng_id, sid):
        pass

class FakeCommEngine:
    def __init__(self):
        self.executor = FakeExecutor()

@pytest.fixture
def fake_deps():
    shopdeck = MockShopdeckAdapter()
    ccc = FakeCCCBuilder()
    comm = FakeCommEngine()
    orch = FakeOrchestrator()
    return shopdeck, ccc, comm, orch

@pytest.mark.asyncio
async def test_max_1_strictly_sequential(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    
    # 2 items
    shopdeck.queue = [{"queue_item_id": "q1", "awb_no": "1"}, {"queue_item_id": "q2", "awb_no": "2"}]
    
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=1, poll_interval_seconds=1)
    
    # We will run the poll loop briefly
    poller.start()
    await asyncio.sleep(0.3) # time for both to process sequentially (each takes ~0.1s)
    await poller.stop()
    
    assert comm.executor.max_concurrent_observed == 1
    assert len(comm.executor.dispatch_calls) == 2
    
@pytest.mark.asyncio
async def test_max_5_allows_overlap(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    
    # 5 items
    for i in range(5):
        shopdeck.queue.append({"queue_item_id": f"q{i}", "awb_no": str(i)})
        
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=5, poll_interval_seconds=1)
    
    poller.start()
    await asyncio.sleep(0.15) # Since all 5 overlap, they should finish in slightly > 0.1s
    await poller.stop()
    
    # They should have overlapped!
    assert comm.executor.max_concurrent_observed == 5
    assert len(comm.executor.dispatch_calls) == 5

@pytest.mark.asyncio
async def test_sixth_item_waits(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    
    for i in range(6):
        shopdeck.queue.append({"queue_item_id": f"q{i}", "awb_no": str(i)})
        
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=5, poll_interval_seconds=1)
    
    poller.start()
    # At t=0.05, 5 are active, 1 is waiting
    await asyncio.sleep(0.05)
    assert comm.executor.max_concurrent_observed == 5
    assert len(poller._active_tasks) == 5
    # The 6th is stuck trying to acquire semaphore, so shopdeck queue should have 0 items left but active tasks is 5
    # Wait, the claim loop happens sequentially. It claims 5, spawns 5 tasks. Semaphore reaches 0.
    # The 6th loop iteration blocks on semaphore.acquire(), before calling claim_ndr_work.
    # So queue should still have 1 item!
    assert len(shopdeck.queue) == 1
    
    await asyncio.sleep(0.2) # Allow all to finish
    await poller.stop()
    assert len(comm.executor.dispatch_calls) == 6

@pytest.mark.asyncio
async def test_empty_queue_releases_slot(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    shopdeck.queue = [] # Empty!
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=1, poll_interval_seconds=0)
    
    poller.start()
    await asyncio.sleep(0.05)
    await poller.stop()
    
    assert poller._semaphore._value == 1 # Semaphore should be available

@pytest.mark.asyncio
async def test_exception_in_dispatch_releases_slot(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    shopdeck.queue = [{"queue_item_id": "q1", "awb_no": "1"}, {"queue_item_id": "q2", "awb_no": "2"}]
    
    # Force first dispatch to fail
    async def bad_dispatch(*args, **kwargs):
        raise RuntimeError("boom")
    comm.executor.dispatch_provider_call = bad_dispatch
    
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=1, poll_interval_seconds=0)
    
    poller.start()
    await asyncio.sleep(0.1)
    await poller.stop()
    
    # Second one should have been able to run (or attempt to run), meaning slot was released
    assert poller._semaphore._value == 1
    # Check that shopdeck was polled multiple times
    assert len(shopdeck.queue) == 0

@pytest.mark.asyncio
async def test_duplicate_item_handled_gracefully(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    # Simulate claiming an item that was already dispatched (current_engagement populated)
    shopdeck.queue = [{
        "queue_item_id": "q1", 
        "awb_no": "1", 
        "current_engagement": {"engagement_id": "eng_1", "call_sid": "sid_1"}
    }]
    
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=1, poll_interval_seconds=0)
    
    poller.start()
    await asyncio.sleep(0.1)
    await poller.stop()
    
    # Should skip dispatch
    assert comm.executor.active_dispatches == 0
    assert len(comm.executor.dispatch_calls) == 0
    # Slot released
    assert poller._semaphore._value == 1

@pytest.mark.asyncio
async def test_clean_shutdown_awaits_tasks(fake_deps):
    shopdeck, ccc, comm, orch = fake_deps
    shopdeck.queue = [{"queue_item_id": "q1", "awb_no": "1"}]
    
    poller = NDRQueuePoller(shopdeck, ccc, comm, orch, max_concurrent_calls=1, poll_interval_seconds=0)
    
    poller.start()
    await asyncio.sleep(0.01) # task spawned but still sleeping in dispatch
    assert len(poller._active_tasks) == 1
    
    # Stop should block until task finishes
    await poller.stop()
    assert len(poller._active_tasks) == 0
    assert len(comm.executor.dispatch_calls) == 1
