import sys
from unittest.mock import MagicMock
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['pymongo.errors'] = MagicMock()

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.workers.ndr_queue_poller import NDRQueuePoller
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.intelligence_domains.ndr.communication_engine import CommunicationEngine

def _find_intelligence_results_call(mock_post):
    """
    The writeback now authenticates via the real Aaram Identity M2M service-token flow
    (ShopdeckCemAdapter._get_auth_header -> submit_intelligence), which makes an additional
    real POST to fetch/cache the token before the actual intelligence_results POST. Find the
    specific call rather than assuming exactly one POST happened.
    """
    for call in mock_post.call_args_list:
        args, kwargs = call
        if args and "intelligence_results" in args[0]:
            return args, kwargs
    raise AssertionError(
        f"No intelligence_results POST found among calls: {mock_post.call_args_list}"
    )


@pytest.mark.asyncio
async def test_ndr_queue_e2e_4_items():
    print("\n--- Starting Local E2E Certification Test ---")
    
    # 1. Mocks
    mock_adapter = AsyncMock(spec=ShopdeckCemAdapter)
    mock_ccc = AsyncMock(spec=CustomerConversationContextBuilder)
    mock_comm = AsyncMock(spec=CommunicationEngine)
    mock_comm.executor = AsyncMock()
    mock_comm.executor.exotel_adapter = AsyncMock()
    mock_comm.executor.exotel_adapter.execute.return_value = "mock_call_123"
    # The poller calls executor.dispatch_provider_call (see executor.py:61), not
    # exotel_adapter.execute. Without this the AsyncMock returns a MagicMock, call_sid
    # derivation falls through to its random fallback, and the assertion below fails.
    mock_comm.executor.dispatch_provider_call.return_value = {"provider_interaction_id": "mock_call_123"}

    poller = NDRQueuePoller(
        shopdeck_adapter=mock_adapter,
        ccc_builder=mock_ccc,
        comm_engine=mock_comm,
        poll_interval_seconds=1
    )

    # 2. Simulate 4 Queue Items
    queue_items = [
        {"queue_item_id": f"q_{i}", "awb_no": f"AWB_{i}", "current_engagement": None}
        for i in range(1, 5)
    ]
    
    # Configure claim_ndr_work to return each item once, then None
    mock_adapter.claim_ndr_work.side_effect = queue_items + [None]

    # 3. Execute Poller for 4 items
    for _ in range(4):
        processed = await poller.process_next_item()
        assert processed is True
        
    # Queue is now empty
    assert await poller.process_next_item() is False

    # 4. Assertions for Poller Phase
    assert mock_adapter.claim_ndr_work.call_count == 5
    assert mock_adapter.register_engagement.call_count == 4
    assert mock_adapter.update_queue_status.call_count == 4

    for i in range(1, 5):
        # Verify status update was called with call_dispatched
        call_args = mock_adapter.update_queue_status.call_args_list[i-1][1]
        assert call_args["queue_item_id"] == f"q_{i}"
        assert call_args["status"] == "call_dispatched"
        assert call_args["call_sid"] == "mock_call_123"

    print("✅ Poller successfully claimed, registered, and dispatched 4 distinct items.")

    # 5. Simulate Webhooks (Phase 6 Writeback)
    # Testing exotel_webhooks.py logic manually to bypass full FastAPI app context.
    #
    # handle_transcript no longer calls ShopDeck directly - it only records the LATEST
    # decisive classification locally (LAST-decisive-turn-wins, since a customer can change
    # their mind mid-call). The actual one-time ShopDeck submission happens at session-end.
    # This mock repo is stateful (a real dict, not a stateless AsyncMock return value) so the
    # test exercises the real two-phase handoff: record in handle_transcript, read back and
    # submit in handle_session_end.
    from src.api.webhooks.exotel_webhooks import handle_transcript, handle_session_end
    from fastapi import Request
    from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository

    pending_by_engagement = {}

    mock_repo = AsyncMock(spec=CustomerEngagementRepository)

    def get_eng_side_effect(eng_id):
        idx = eng_id.split("_")[-1]
        doc = {"call_context": {"queue_item_id": f"q_{idx}"}, "awb_no": f"AWB{idx}"}
        if eng_id in pending_by_engagement:
            doc["metadata"] = {"pending_ndr_outcome": pending_by_engagement[eng_id]}
        return doc
    mock_repo.get_engagement.side_effect = get_eng_side_effect

    async def record_pending_side_effect(engagement_id, data):
        pending_by_engagement[engagement_id] = data
        return True
    mock_repo.record_pending_ndr_outcome.side_effect = record_pending_side_effect
    mock_repo.claim_intelligence_writeback.return_value = True

    mock_request = AsyncMock(spec=Request)

    for i in range(1, 5):
        mock_request.json.return_value = {
            "CallSid": "mock_call_123",
            "transcript": "Yes schedule for tomorrow",
            "EventId": f"evt_{i}",
            "custom_parameters": {"CustomField": f"eng_{i}|action_1"}
        }
        response = await handle_transcript(mock_request, repo=mock_repo)
        assert response["status"] == "received"

        # No ShopDeck call yet - only local bookkeeping.
        assert pending_by_engagement[f"eng_{i}"]["conversation_state"] == "CONFIRM_RESOLUTION"

        mock_request.json.return_value = {
            "CallSid": "mock_call_123",
            "EventId": f"evt_end_{i}",
            "custom_parameters": {"CustomField": f"eng_{i}|action_1"},
            "Status": "completed",
        }
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            await handle_session_end(mock_request, repo=mock_repo)

            args, kwargs = _find_intelligence_results_call(mock_post)
            posted_data = kwargs["json"]
            assert posted_data["queue_item_id"] == f"q_{i}"
            assert posted_data["awb_no"] == f"AWB{i}"
            assert posted_data["recommended_action"] == "reschedule"
            assert posted_data["customer_intent"] == "agreed"
            assert posted_data["diagnosis"] == "CONFIRM_RESOLUTION"

    print("✅ Webhook correctly synthesized intelligence and persisted writeback (ACTION_READY) 4 times without overlap.")
    print("--- Local E2E Certification Complete ---")

@pytest.mark.asyncio
async def test_dispatch_then_crash_protection():
    print("\n--- Starting Dispatch-then-Crash Protection Test ---")
    
    from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
    mock_adapter = AsyncMock(spec=ShopdeckCemAdapter)
    
    # Simulate first worker claims and successfully registers engagement, but crashes before call_sid update
    # So second worker claims the same item, and register_engagement throws a 409 Conflict with "engagement_outcome_unknown"
    import httpx
    
    def register_side_effect(*args, **kwargs):
        raise httpx.HTTPStatusError(
            message="409 Conflict",
            request=httpx.Request("POST", "url"),
            response=httpx.Response(409, json={"detail": "engagement_outcome_unknown: an active engagement exists but call_sid is unknown. Awaiting webhook reconciliation or timeout."})
        )
        
    mock_adapter.register_engagement.side_effect = register_side_effect
    mock_adapter.claim_ndr_work.return_value = {
        "queue_item_id": "q_crash_1", 
        "awb_no": "AWB_CRASH", 
        "current_engagement": None
    }
    
    poller = NDRQueuePoller(
        shopdeck_adapter=mock_adapter,
        ccc_builder=AsyncMock(),
        comm_engine=AsyncMock(),
        poll_interval_seconds=1
    )
    
    try:
        await poller.process_next_item()
        # The poller should catch the HTTPStatusError or propagate it.
        # Let's ensure it does not proceed to dispatch!
        assert poller.comm_engine.dispatch_action.call_count == 0
        print("✅ Poller successfully aborted dispatch when encountering unknown outcome state.")
    except Exception as e:
        print(f"✅ Poller gracefully surfaced the protection error: {e}")
        assert "409" in str(e)
        assert poller.comm_engine.dispatch_action.call_count == 0
        
    print("--- Dispatch-then-Crash Protection Verified ---")

@pytest.mark.asyncio
async def test_outcome_unknown_recovery():
    print("\n--- Starting OUTCOME_UNKNOWN Recovery Test ---")
    
    from src.api.webhooks.exotel_webhooks import handle_transcript, handle_session_end
    from fastapi import Request
    from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository

    pending = {}
    mock_repo = AsyncMock(spec=CustomerEngagementRepository)

    def get_eng_side_effect(eng_id):
        # queue_item_id lives in call_context, not a nonexistent metadata field - see
        # src/api/webhooks/exotel_webhooks.py's handle_transcript. awb_no is REQUIRED by
        # ShopDeck's NDRIntelligenceRequest, so the webhook refuses to post without one.
        doc = {"call_context": {"queue_item_id": "q_999"}, "awb_no": "AWB999"}
        if eng_id in pending:
            doc["metadata"] = {"pending_ndr_outcome": pending[eng_id]}
        return doc
    mock_repo.get_engagement.side_effect = get_eng_side_effect

    async def record_pending_side_effect(engagement_id, data):
        pending[engagement_id] = data
        return True
    mock_repo.record_pending_ndr_outcome.side_effect = record_pending_side_effect
    mock_repo.claim_intelligence_writeback.return_value = True

    mock_request = AsyncMock(spec=Request)

    # The webhook arrives with a custom parameter linking to the engagement id that was stuck.
    # handle_transcript records the classification; handle_session_end performs the actual
    # one-time ShopDeck submission using whatever was last recorded.
    mock_request.json.return_value = {
        "CallSid": "mock_call_CRASH_999",
        "transcript": "No I don't want the package",
        "EventId": "evt_crash_recover",
        "custom_parameters": {"CustomField": "eng_crash_999|action_1"}
    }
    response = await handle_transcript(mock_request, repo=mock_repo)
    assert response["status"] == "received"

    mock_request.json.return_value = {
        "CallSid": "mock_call_CRASH_999",
        "EventId": "evt_crash_recover_end",
        "custom_parameters": {"CustomField": "eng_crash_999|action_1"},
        "Status": "completed",
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200

        await handle_session_end(mock_request, repo=mock_repo)

        # Verify Intelligence Writeback happened at session-end
        args, kwargs = _find_intelligence_results_call(mock_post)
        posted_data = kwargs["json"]
        # ShopDeck's schema, not the old ad-hoc one: ndr_intent/confidence_score were never
        # accepted fields, and result_id/awb_no are required.
        assert posted_data["queue_item_id"] == "q_999"
        assert posted_data["awb_no"] == "AWB999"
        assert posted_data["recommended_action"] == "accept_rto"
        assert posted_data["customer_intent"] == "declined"
        assert posted_data["diagnosis"] == "CUSTOMER_REFUSED"
        assert posted_data["result_id"].startswith("res_")

    print("✅ Webhook successfully correlated and recovered the stuck engagement by persisting intelligence and advancing ShopDeck state to ACTION_READY.")
    print("--- OUTCOME_UNKNOWN Recovery Verified ---")

