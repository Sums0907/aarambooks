import pytest
from unittest.mock import AsyncMock, MagicMock
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ExecutionIntent, ExecutionChannel
from src.infrastructure.adapters.customer_engagement.executor import CustomerEngagementExecutor
from src.infrastructure.adapters.customer_engagement.models import EngagementState

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.create_engagement = AsyncMock()
    repo.transition_state = AsyncMock()
    repo.update_engagement_correlation = AsyncMock()
    return repo

@pytest.fixture
def mock_adapter():
    adapter = AsyncMock()
    adapter.dispatch_call = AsyncMock(return_value={"provider_call_id": "mock_call_id", "call_id": "mock_call_id"})
    return adapter

@pytest.mark.asyncio
async def test_executor_routes_to_adapter_successfully(mock_repo, mock_adapter):
    executor = CustomerEngagementExecutor(repository=mock_repo, exotel_adapter=mock_adapter)
    
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test",
        parameters={"awb_no": "AWB_TEST_456", "customer_phone": "9876543210"},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)
    )
    
    record = await executor.execute_engagement(action)
    
    # 1. Created requested record
    mock_repo.create_engagement.assert_called_once()
    assert record.status == EngagementState.DISPATCHED
    
    # 2. Called physical adapter
    mock_adapter.dispatch_call.assert_called_once_with(action, record.engagement_id)
    
    # 3. Transitioned state to DISPATCHED
    mock_repo.transition_state.assert_called_once_with(record.engagement_id, EngagementState.DISPATCHED)

@pytest.mark.asyncio
async def test_executor_handles_adapter_failure(mock_repo, mock_adapter):
    executor = CustomerEngagementExecutor(repository=mock_repo, exotel_adapter=mock_adapter)
    mock_adapter.dispatch_call = AsyncMock(side_effect=ValueError("Exotel API Error"))
    
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test",
        parameters={"awb_no": "AWB_TEST_456", "customer_phone": "9876543210"},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)
    )
    
    record = await executor.execute_engagement(action)
    
    assert record.status == EngagementState.FAILED
    mock_repo.transition_state.assert_called_once_with(
        mock_repo.create_engagement.call_args[0][0].engagement_id, 
        EngagementState.FAILED
    )

@pytest.mark.asyncio
async def test_no_adapter_configured(mock_repo):
    executor = CustomerEngagementExecutor(repository=mock_repo, exotel_adapter=None)
    
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test",
        parameters={"awb_no": "AWB_TEST_456", "customer_phone": "9876543210"},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)
    )
    
    record = await executor.execute_engagement(action)
    
    assert record.status == EngagementState.FAILED
    mock_repo.transition_state.assert_called_once_with(
        mock_repo.create_engagement.call_args[0][0].engagement_id, 
        EngagementState.FAILED
    )
