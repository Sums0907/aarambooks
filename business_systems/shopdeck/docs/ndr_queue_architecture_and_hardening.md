# ShopDeck BS NDR Queue Architecture & Hardening Guide

This document provides a comprehensive overview of the Non-Delivery Report (NDR) Queue implementation and the robust production hardening applied to it within the ShopDeck Business System (BS).

## 1. Architectural Overview & Philosophy

The foundational principle of this architecture is that **ShopDeck BS is the sovereign authority over NDR operations.** The Brain/Rabta components, NDR-ID, and the external Real ShopDeck platform have strictly defined, segregated roles to prevent race conditions, assure data integrity, and guarantee atomic state management.

### Component Roles

*   **ShopDeck BS (Business System):**
    *   **Owns completely:** The NDR queue state machine, eligibility rules, claim/lease semantics (leasing work to agents), retry logic tracking, correlation between the physical call/engagement and the queue item, and durable persistence of both the call transcript (engagement) and the resulting intelligence.
    *   **Controls:** What actions are recommended based on intelligence and when a queue item transitions to an actionable state (`action_ready`).
    *   **Guarantees:** Idempotency, atomicity, and ownership enforcement.

*   **Brain / Rabta:**
    *   **Role:** Acts as the consumer and orchestrator.
    *   **Action:** Claims work from the ShopDeck BS NDR queue via the API. Processes the work by invoking the Customer Engagement service (e.g., Exotel/Priya) to perform physical telephony. Receives the transcript, sends it to the intelligence service (NDR-ID), and submits the resulting intelligence back to ShopDeck BS.
    *   **Constraint:** Never selects arbitrary AWBs. Never accesses the ShopDeck PostgreSQL database directly. Only communicates via the formal API.

*   **NDR-ID (Intelligence Engine):**
    *   **Role:** Purely analytical.
    *   **Action:** Generates intelligence (intents, diagnoses, recommended actions) based on the call transcript.
    *   **Constraint:** Does *not* own queue state. Does *not* mutate the ShopDeck DB directly. Does *not* select AWBs.

*   **Real ShopDeck Platform (MCP):**
    *   **Role:** The source of truth for raw logistics events (Shipment tracking, etc.).
    *   **Constraint:** Treated strictly as **READ-ONLY** by this workflow. The NDR intelligence workflow never assumes write capabilities to the actual downstream ShopDeck platform directly.

## 2. The Database Data Model

The data model is designed to correlate the entire lifecycle of an NDR event cleanly. 

1.  **`shipment_ndr_reports`**: The source table aggregating raw NDR events. This table represents the physical reality of the package delivery lifecycle.
2.  **`ndr_queue`**: The operational work queue. Items are enrolled into this queue from `shipment_ndr_reports` based on specific eligibility criteria. It tracks lease times, claim attempts, and the overarching status of the NDR resolution process.
3.  **`ndr_engagements`**: Represents the physical action taken to resolve the NDR (e.g., placing an Exotel call). It is firmly linked to a specific `queue_item_id`.
4.  **`ndr_intelligence_results`**: Stores the final, durable artifact produced by NDR-ID, representing the actionable intelligence gathered from the engagement.

## 3. Production Hardening Constraints Implemented

To ensure the system remains resilient under highly concurrent, distributed loads (e.g., multiple Brain nodes operating simultaneously), a massive hardening and certification pass was implemented.

### 3.1. Atomicity & Concurrency Enforcement
*   **Problem:** Brain nodes could potentially race, causing multiple engagements to be created for the same queue item simultaneously, or causing state transitions to be lost.
*   **Solution:** All critical operational mutations were wrapped in strict PostgreSQL transactional blocks (`BEGIN ... COMMIT`) within the repository layer.
*   **Implementation:** Used `SELECT * FROM ndr_queue WHERE queue_item_id = $1 FOR UPDATE` within `register_engagement_atomic` and `persist_intelligence_atomic`. This ensures that from the moment a state check begins until the final data is written and the queue status is transitioned, the row is strictly locked at the database level.

### 3.2. Claim Live Guard & Lease Semantics
*   **Problem:** An AWB might be delivered or returned to the origin *after* it was enrolled in the queue but *before* a Brain node claimed it. This could result in a physical call to a customer who already received their package.
*   **Solution:** The "Live Guard". 
*   **Implementation:** The `claim_next_eligible` query dynamically performs an `INNER JOIN` against the `shipment_ndr_reports` table at the exact moment of the claim. It enforces real-time state checks (`ndr_status = 'pending'`, `order_status = 'dispatched'`, and `delivery_time IS NULL`).
*   **Concurrency Safe:** Used `FOR UPDATE SKIP LOCKED` to allow multiple Brain nodes to claim distinct items concurrently without blocking or deadlocking each other.

### 3.3. Claimer Ownership Enforcement & RBAC
*   **Problem:** Brain node B could accidentally (or maliciously) transition the state of a queue item that was legitimately leased to Brain node A.
*   **Solution:** Strict ownership validation.
*   **Implementation:** The API now extracts the `sub` (identity) from the RS256 verified JWT (`claimer_id`). Every state transition, engagement creation, or intelligence persistence strictly enforces that `row["claimed_by"] == claimer_id`. If they differ, the transaction aborts with a `PermissionError` (403 Forbidden). 
*   **RBAC:** A new dependency `get_current_user_edit` explicitly mandates the `SHOPDECK_EDIT` permission for any route that mutates queue state.

### 3.4. Engagement Crash Recovery & Idempotency
*   **Problem:** A Brain node claims an item, registers an engagement to obtain an `engagement_id`, dispatches the physical call, and then immediately crashes. When the lease expires, another Brain node claims the item. It must not place a *second* physical call.
*   **Solution:** The database enforces a `UNIQUE` index constraint `WHERE is_active = TRUE` on `ndr_engagements`. 
*   **Idempotency Keys:** Engagements require an `idempotency_key`. If the same key is submitted, the DB idempotently returns the existing `engagement_id`.
*   **Active Call Prevention:** The `register_engagement_atomic` transaction explicitly checks if an active engagement already exists with a populated `call_sid`. If it does, the repository throws a `ValueError` preventing a duplicate outbound physical call.

### 3.5. Intelligence Idempotency 
*   **Problem:** Retries during the final intelligence persistence phase could lead to duplicate result rows, or worse, conflicting intelligence artifacts attached to the same engagement.
*   **Solution:** `persist_intelligence_atomic` performs a deep equality check on the incoming payload against any existing payload with the same `result_id`.
*   **JSONB Equality:** It verifies that immutable fields match and uses `json.dumps()` to guarantee that nested `action_parameters` and `source_evidence` dicts match exactly before successfully returning a 200 OK (Idempotent Success) rather than 201 Created. Conflicting data throws a 409 Conflict.

### 3.6. JSONB Serialization Patches
*   **Problem:** `asyncpg` combined with Python dictionaries natively produces `asyncpg.exceptions.DataError` or `schema mismatches` when inserting into `JSONB` columns natively depending on the pool encoding config.
*   **Solution:** All JSON inserts inside the repository are safely passed through `json.dumps()` explicitly. On the read path (e.g., in `get_action_ready`), stringified JSON fetched from the DB is safely parsed via `json.loads()` before being injected into the Pydantic response models.

## 4. Aaram Brain Evolution Integration (Outbound Queues & Concurrent Polling)

To support the Aaram Brain's transition from synchronous webhooks to a high-throughput, fault-tolerant asynchronous Outbound Writeback Queue, the ShopDeck boundary was overhauled to guarantee mathematical safety under process-local bounded concurrency.

### 4.1 Concurrent Dispatch Orchestration
*   **The Problem:** The Brain's `NDRQueuePoller` was upgraded to use an `asyncio.Semaphore` to process up to 5 concurrent NDR claims simultaneously.
*   **The ShopDeck Guarantee:** ShopDeck mathematically guarantees safe concurrent leasing without race conditions. The `claim_next_eligible` query leverages `FOR UPDATE OF q SKIP LOCKED` within an `async with conn.transaction()` block. If 5 concurrent POST requests hit the `/claim` endpoint in the exact same millisecond, PostgreSQL locks the top eligible row for the first request and forces the other 4 connections to gracefully skip the locked row and claim the subsequent items.

### 4.2 Outbound Writeback Idempotency (Zero Data Loss)
*   **The Problem:** The Brain now persists intelligence payloads to a local MongoDB `Outbox` and uses an asynchronous `OutboundWritebackWorker` to guarantee delivery to ShopDeck. This worker may retry payloads multiple times during network failures.
*   **The ShopDeck Guarantee:** The `/intelligence_results` endpoint uses the Brain-assigned `result_id` as a strict idempotency key. The `persist_intelligence_atomic` repository method checks for duplicate `result_id`s. If found, it validates that all immutable fields match exactly. Instead of throwing a 409 Conflict, it safely swallows the duplicate and returns `{"status": "duplicate"}`, which the router translates into an HTTP 200 OK. This gracefully acknowledges the Brain's retry and allows the Outbox to mark the payload as delivered.

### 4.3 PBAC M2M Authentication Boundary
*   **The Problem:** External Brain nodes require mathematically verifiable authorization to mutate ShopDeck state.
*   **The ShopDeck Guarantee:** All integration endpoints (`/claim`, `/{queue_item_id}/status`, and `/intelligence_results`) are heavily fortified behind `get_current_user` and `get_current_user_edit` dependencies. The identity of the Brain is verified via RS256 JWT tokens. Furthermore, the `claimer_id` extracted from the token's `sub` claim is strictly validated against `row["claimed_by"]` during any state transition, ensuring a malicious or misconfigured node cannot hijack another node's leased queue item.

## 5. Final Deployment Topology

The final deployment ensures all communication runs through proper service channels. 
*   The `docker-compose.prod.yml` securely injects the `IDENTITY_API_URL`.
*   The API operates securely on port `8210`.
*   Test and scratch artifacts have been aggressively pruned to ensure production security environments remain clean of synthetic artifacts or private key exposures.
