# NDR Concurrent Polling Architecture

## The Problem
Initially, the `NDRQueuePoller` in the Brain operated in a strictly sequential manner. It would pull one item from the ShopDeck queue, hydrate the Customer Conversation Context (CCC), send instructions to the AI Orchestrator, trigger the Exotel VoiceBot API, wait for that entire process to finish, and *only then* pull the next item from the queue.

While extremely safe, this became a bottleneck. The Exotel API dispatch involves multiple network hops and LLM text-generation cycles, taking up to 2-4 seconds per call. If there were 100 items in the queue, it would take several minutes just to trigger the calls, even though Exotel could easily handle thousands of simultaneous active calls. 

We needed a way to trigger Exotel dispatches in parallel, without accidentally duplicating claims or corrupting state.

## The Concurrency Strategy
We implemented a strict, bounded **Process-Local Orchestration Concurrency** strategy, controlled by the `NDR_MAX_CONCURRENT_CALLS` environment variable.

### 1. The Semaphore Throttle
The Brain's polling loop is controlled by an `asyncio.Semaphore`. If `NDR_MAX_CONCURRENT_CALLS=5`, there are exactly 5 "slots" available.
- The poller loop acquires a slot.
- It makes an HTTP `POST /api/v1/ndr/queue/claim` to ShopDeck.
- It hands the claimed item off to a background task (`_process_task_wrapper`).
- The poller loop immediately moves on to acquire the next slot, allowing it to pull up to 5 items overlapping in time.
- Once all 5 slots are acquired, the poller completely blocks. It will not touch ShopDeck again until one of the background tasks finishes dispatching Exotel and releases its slot.

### 2. ShopDeck: The Source of Truth
We explicitly avoided introducing distributed locks (like Redis) inside the Brain. **ShopDeck Business System remains the authoritative source of truth.**
When the Brain calls `/api/v1/ndr/queue/claim`, the ShopDeck PostgreSQL database executes the following atomic lock:
```sql
SELECT q.queue_item_id FROM ndr_queue q
...
FOR UPDATE OF q SKIP LOCKED
```
This mathematical guarantee ensures that even if 5 parallel HTTP requests arrive from the Brain at the exact same millisecond, ShopDeck will safely dispense 5 completely distinct, non-overlapping queue items.

### 3. Idempotency & The Boundary
The concurrency boundary strictly ends at the orchestration phase. 
Once the background task triggers Exotel, the physical phone call itself takes minutes. The Brain does not hold a slot open for the duration of the physical phone call. It only holds the slot open for the *dispatch* (the act of instructing Exotel to dial the phone).

The strict idempotency lifecycle remains sequential per item:
1. **Atomic Claim:** ShopDeck grants a unique row.
2. **Engagement Registration:** The Brain upserts an engagement record in MongoDB.
3. **Exotel Dispatch:** The Brain commands Exotel.
4. **Correlation Persistence:** The `call_sid` is linked.

If any error occurs (network failure, LLM failure), the `finally` block in the background task guarantees the semaphore slot is released so the poller does not deadlock.

## Conclusion
This architecture allows the Brain to safely orchestrate thousands of calls per hour by fanning out the slow API requests, entirely relying on PostgreSQL's row-level locking to prevent race conditions and duplicate operations. It preserves the absolute invariant: **Brain owns intelligence, ShopDeck owns state.**
