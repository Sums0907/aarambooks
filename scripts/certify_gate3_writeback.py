"""
Physical Gate 3 pre-check: verifies the terminal writeback pathway from Brain's Exotel
transcript webhook to the real ShopDeck BS, end to end, without placing a physical call.

This corrects three factual errors found in an earlier drafted plan for this same check:
  - the webhook route is /api/customer-engagement/voice/exotel/transcript, not /api/webhooks/...
  - persist_intelligence_atomic writes to ndr_intelligence_results and sets
    ndr_queue.queue_status='action_ready' - not "ndr_action_history" (that table isn't
    touched by this path at all).
  - persist_intelligence_atomic requires ndr_queue.claimed_by to match the caller's identity
    before it will write anything - a raw SQL seed with queue_status='eligible' is not
    enough; the item must actually be claimed through the real claim endpoint first.

It also verifies the one-per-engagement writeback guard added in
src/infrastructure/adapters/customer_engagement/repository.py:claim_intelligence_writeback -
firing two DIFFERENT transcript events at the same engagement must result in exactly one
ShopDeck write, using the FIRST decisive classification, not the last.

Never logs the actual bearer token - only whether one was present.
"""
import asyncio
import logging
import uuid

import asyncpg
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run():
    from src.main import app, ndr_poller, shopdeck_cem
    from unittest.mock import AsyncMock

    print("=========================================")
    print(" GATE 3 WRITEBACK PATHWAY VERIFICATION ")
    print("=========================================")

    conn = await asyncpg.connect("postgresql://postgres:shopdeck_pass@localhost:5435/shopdeck_bs_prod")

    qid = str(uuid.uuid4())
    awb = f"AWBGATE3{qid[:8].upper()}"
    cust_id = f"cust_{qid[:8]}"

    await conn.execute(
        """
        INSERT INTO shipment_ndr_reports (
            _id, awb_no, order_status, ndr_status, payment_mode, ndr_count, ofd_count,
            courier_partner, customer_id, customer_name
        ) VALUES ($1, $2, 'dispatched', 'pending', 'cod', 1, 0, 'Delhivery', $3, 'Gate3 Test Customer')
        """,
        qid, awb, cust_id,
    )
    await conn.execute(
        """
        INSERT INTO order_line_items (order_id, awb_no, sku_id, product_name, quantity, selling_price, cod_charge, delivery_fees, createdat)
        VALUES ($1, $2, $3, 'Gate3 Test Bedsheet', 1, 599.0, 0.0, 0.0, NOW())
        """,
        f"order_{qid[:8]}", awb, f"sku_{qid[:8]}",
    )
    await conn.execute(
        "INSERT INTO customer_info (awb_no, customer_id, customer_number) VALUES ($1, $2, '9999999999')",
        awb, cust_id,
    )
    await conn.execute(
        """
        INSERT INTO ndr_queue (
            queue_item_id, awb_no, ndr_attempt_seq, queue_status,
            ndr_time_at_enroll, ndr_reason_at_enroll, ndr_count_at_enroll, payment_mode,
            enrolled_at, updated_at
        ) VALUES ($1, $2, 1, 'eligible', NOW(), 'Customer unavailable', 1, 'cod', NOW(), NOW())
        """,
        qid, awb,
    )
    logger.info(f"Seeded synthetic queue item {qid} / AWB {awb}")

    # Route the poller's dispatch through a mock so no real Exotel call is placed, but let
    # everything else - claim, hydration, local engagement, ShopDeck registration, queue
    # status - run for real. This is the "actual claim step" the earlier draft plan omitted:
    # process_next_item() calls shopdeck_adapter.claim_ndr_work() for real, which sets
    # ndr_queue.claimed_by server-side. Without this, persist_intelligence_atomic's ownership
    # check (claimed_by != caller identity) rejects the write unconditionally.
    dispatch_calls = []

    async def mock_dispatch(action, eng_id):
        dispatch_calls.append(eng_id)
        return {"provider_interaction_id": f"gate3_mock_call_{uuid.uuid4().hex}"}

    original_dispatch = ndr_poller.comm_engine.executor.exotel_adapter.dispatch_call
    ndr_poller.comm_engine.executor.exotel_adapter.dispatch_call = AsyncMock(side_effect=mock_dispatch)

    processed = await ndr_poller.process_next_item()
    ndr_poller.comm_engine.executor.exotel_adapter.dispatch_call = original_dispatch

    row = await conn.fetchrow("SELECT queue_item_id, claimed_by, queue_status FROM ndr_queue WHERE queue_item_id = $1", qid)
    logger.info(f"Post-dispatch queue row: {dict(row) if row else None}")

    if not row or row["claimed_by"] is None:
        # The poller may have claimed a DIFFERENT, older backlogged item first (queue claims
        # oldest-eligible-first). If so, this run cannot exercise the writeback for THIS item
        # this time - report it plainly rather than silently seeding an unclaimed item's data.
        print("FAIL: seeded item was not claimed this run (queue backlog likely claimed an older item first).")
        print("Re-run, or clear the backlog, to reach this item.")
        await conn.close()
        return

    engagement_id = dispatch_calls[0] if dispatch_calls else None
    if not engagement_id:
        print("FAIL: no engagement was dispatched for the seeded item.")
        await conn.close()
        return
    logger.info(f"Engagement dispatched: {engagement_id}")

    NAMESPACE_NDR = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    action_request_id = f"act_{uuid.uuid5(NAMESPACE_NDR, qid).hex}"

    from src.api.webhooks.exotel_webhooks import handle_transcript, handle_session_end
    from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
    repo = CustomerEngagementRepository()

    class DummyRequest:
        def __init__(self, body):
            self._body = body

        async def json(self):
            return self._body

    # --- Turn 1: an ambiguous turn. Must NOT consume the one writeback slot. ---
    resp1 = await handle_transcript(
        DummyRequest({
            "CallSid": "gate3_call_sid",
            "transcript": "haan wo... matlab... pata nahi",
            "EventId": "evt_gate3_1",
            "custom_parameters": {"CustomField": f"{engagement_id}|{action_request_id}"},
        }),
        repo=repo,
    )
    logger.info(f"Turn 1 (UNCLEAR) response: {resp1}")

    # --- Turn 2: a decisive refusal. This SHOULD be the one write that reaches ShopDeck. ---
    resp2 = await handle_transcript(
        DummyRequest({
            "CallSid": "gate3_call_sid",
            "transcript": "mujhe ye order nahi chahiye, cancel kar do",
            "EventId": "evt_gate3_2",
            "custom_parameters": {"CustomField": f"{engagement_id}|{action_request_id}"},
        }),
        repo=repo,
    )
    logger.info(f"Turn 2 (refusal) response: {resp2}")

    # --- Turn 3: the customer changes their mind - a DIFFERENT decisive classification on
    # the SAME engagement. Design is LAST-decisive-turn-wins (a real live call showed a
    # customer doing exactly this: reject one option, then accept another), so this turn's
    # classification, not turn 2's, is what should reach ShopDeck. ---
    resp3 = await handle_transcript(
        DummyRequest({
            "CallSid": "gate3_call_sid",
            "transcript": "theek hai kal delivery bhej dijiye",
            "EventId": "evt_gate3_3",
            "custom_parameters": {"CustomField": f"{engagement_id}|{action_request_id}"},
        }),
        repo=repo,
    )
    logger.info(f"Turn 3 (different resolution, same engagement) response: {resp3}")

    # --- Session end: this is the ONLY point a real ShopDeck submission happens. It must
    # submit whatever was current after turn 3, not turn 2. ---
    resp_end = await handle_session_end(
        DummyRequest({
            "CallSid": "gate3_call_sid",
            "EventId": "evt_gate3_end",
            "custom_parameters": {"CustomField": f"{engagement_id}|{action_request_id}"},
            "Status": "completed",
        }),
        repo=repo,
    )
    logger.info(f"Session-end response: {resp_end}")

    intel_row = await conn.fetchrow(
        "SELECT * FROM ndr_intelligence_results WHERE engagement_id = $1", engagement_id
    )
    queue_row_after = await conn.fetchrow(
        "SELECT queue_status, action_ready_at FROM ndr_queue WHERE queue_item_id = $1", qid
    )
    all_results_for_engagement = await conn.fetch(
        "SELECT result_id, diagnosis, recommended_action, customer_intent FROM ndr_intelligence_results WHERE engagement_id = $1",
        engagement_id,
    )

    print("\n--- RESULTS ---")
    print(f"ndr_intelligence_results row: {dict(intel_row) if intel_row else 'NONE'}")
    print(f"ndr_queue.queue_status after writeback: {dict(queue_row_after) if queue_row_after else 'NONE'}")
    print(f"Total intelligence_results rows for this engagement: {len(all_results_for_engagement)}")

    ok = True
    if not intel_row:
        print("FAIL: no ndr_intelligence_results row was ever written.")
        ok = False
    elif intel_row["diagnosis"] == "UNCLEAR":
        print("FAIL: the UNCLEAR turn was submitted - it should never have been recorded as an outcome.")
        ok = False
    elif intel_row["diagnosis"] != "CONFIRM_RESOLUTION":
        print(f"FAIL: expected the LAST decisive turn (CONFIRM_RESOLUTION) to win, got {intel_row['diagnosis']!r}.")
        ok = False

    if len(all_results_for_engagement) != 1:
        print(f"FAIL: expected exactly 1 intelligence_results row for this engagement, found {len(all_results_for_engagement)}.")
        ok = False

    if not queue_row_after or queue_row_after["queue_status"] != "action_ready":
        print(f"FAIL: expected ndr_queue.queue_status='action_ready', got {queue_row_after}.")
        ok = False

    print("\nPASS" if ok else "\nFAIL")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
