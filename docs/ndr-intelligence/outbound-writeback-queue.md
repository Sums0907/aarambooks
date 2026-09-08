# Outbound Writeback Queue Architecture

## The Problem
In the initial NDR Engine architecture, when an Exotel call finished, the `handle_session_end` webhook would immediately try to synchronize the AI's final classification (the "intelligence") to the ShopDeck Business System via a synchronous HTTP POST.

This created a severe reliability risk:
1. **Webhook Timeouts:** If ShopDeck was slow, the webhook would timeout, and Exotel would assume the brain failed.
2. **Data Loss:** If ShopDeck was temporarily unavailable (network blip, deployment, etc.), the intelligence was completely lost because the webhook failed and dropped the payload. The physical call was made, the customer spoke, but ShopDeck never received the result.
3. **Inconsistent State:** The engagement would remain stuck in `COMPLETED` or `OUTCOME_UNKNOWN` in the Brain, but ShopDeck would still think the NDR item was `pending`.

## The Outbound Writeback Queue Pattern
To fix this, we implemented the **Outbound Writeback Queue (Outbox Pattern)**. 

### Core Strategy
1. **Synchronous Enqueue:** When `handle_session_end` receives the final transcript, it performs the heuristic classification (e.g., determining `RESCHEDULE` vs. `RTO_CONFIRMED`). However, instead of making an HTTP call to ShopDeck, it immediately writes this intelligence payload to the local MongoDB database as an `Outbox` record attached to the engagement (`record_pending_ndr_outcome`, then `enqueue_intelligence_writeback`).
2. **Immediate Webhook Response:** The webhook immediately returns HTTP 200 to Exotel. This guarantees Exotel is never blocked and no timeouts occur.
3. **Asynchronous Polling Worker:** A dedicated background daemon (`OutboundWritebackWorker`) constantly polls the database for engagements that have pending writebacks. 
4. **Resilient Dispatch:** The worker attempts to POST the payload to ShopDeck.
   - If it succeeds, the worker marks the writeback as `completed` and the engagement moves to `ACTION_READY`.
   - If it fails, the worker gracefully sleeps and retries. 

### State Machine & Lease Recovery
- **Lease Mechanism:** When the worker claims a pending writeback, it sets a timestamp `writeback_lease_expires_at`. This prevents two worker processes from attempting to send the same data at the same time.
- **Crash Recovery:** If the worker crashes mid-dispatch, the lease naturally expires after 60 seconds. The next worker loop will pick it up and retry it. 

### Idempotency
ShopDeck expects `queue_item_id` and an immutable `result_id` (generated deterministically by the Brain). If ShopDeck actually received the payload but the Brain crashed before recording the success, the Brain will retry. ShopDeck will safely acknowledge the duplicate `result_id` without corrupting state.

### Conclusion
By adopting the Outbox pattern, the Brain achieved **zero data loss** for physical calls. The Exotel network boundary is completely isolated from the ShopDeck business system boundary, connected only by a highly resilient asynchronous worker queue.
