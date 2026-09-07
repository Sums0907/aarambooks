import pytest
import uuid
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ExecutionIntent, ExecutionChannel
from src.intelligence_domains.ndr.models import NDRContext, CustomerState, InterventionRecommendation
from src.intelligence_domains.ndr.knowledge import NDRStrategyEngine
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.intelligence_domains.ndr.communication_engine import CommunicationEngine
from src.infrastructure.adapters.customer_engagement.executor import CustomerEngagementExecutor
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.exotel_adapter import ExotelVoiceBotAdapter

@pytest.fixture
def mock_ndr_context():
    return NDRContext(
        awb_no="AWB_TEST_123",
        courier_partner="DELHIVERY",
        attempt_count=1,
        customer_phone="+919876543210"
    )

@pytest.fixture
def mock_customer_state():
    return CustomerState(preferred_reattempt_date="Tomorrow")

def test_ndr_strategy_voice_execution_intent(mock_ndr_context, mock_customer_state):
    """Test that a valid NDR VOICE recommendation gets explicit ExecutionIntent and customer_phone."""
    strategy, recommendation = NDRStrategyEngine.determine_strategy(
        context=mock_ndr_context,
        # Fake a failure diagnosis and risk evaluation for seller reattempt
        diagnosis=type("Diagnosis", (), {"category": "CUSTOMER_UNAVAILABLE", "confidence": 1.0})(),
        risk=type("Risk", (), {"policy_allows_autonomous_action": True, "customer_experience_risk_score": 0.5})(),
        customer_state=mock_customer_state
    )
    
    assert recommendation.action_type == "seller_reattempt"
    assert recommendation.execution_intent is not None
    assert recommendation.execution_intent.channel == ExecutionChannel.VOICE
    assert recommendation.execution_intent.intent_type == "CUSTOMER_OUTREACH"
    assert recommendation.parameters.get("customer_phone") == "+919876543210"

@pytest.mark.asyncio
async def test_action_request_id_generation(mock_ndr_context, mock_customer_state):
    """Test that a NEW action_request_id is generated and is distinct from recommendation_id."""
    strategy, recommendation = NDRStrategyEngine.determine_strategy(
        context=mock_ndr_context,
        diagnosis=type("Diagnosis", (), {"category": "CUSTOMER_UNAVAILABLE", "confidence": 1.0})(),
        risk=type("Risk", (), {"policy_allows_autonomous_action": True, "customer_experience_risk_score": 0.5})(),
        customer_state=mock_customer_state
    )
    
    orchestrator = NDRIntelligenceOrchestrator(gateway=None, knowledge=None, memory=None)
    
    # Simulate step 9 of orchestrate_resolution
    action = ActionRequest(
        action_request_id=f"act_{uuid.uuid4().hex[:8]}",
        category=recommendation.action_category,
        reasoning=recommendation.justification,
        parameters=recommendation.parameters,
        execution_intent=recommendation.execution_intent
    )
    
    assert action.action_request_id != recommendation.recommendation_id
    assert action.action_request_id.startswith("act_")
    assert recommendation.recommendation_id.startswith("rec_")
    # Intent survives
    assert action.execution_intent == recommendation.execution_intent

@pytest.mark.asyncio
async def test_communication_engine_dispatch_voice():
    """Test CommunicationEngine routes VOICE only when explicitly declared."""
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test",
        parameters={},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)
    )
    
    class MockExecutor:
        executed = False
        async def execute_engagement(self, action_request, **kwargs):
            self.executed = True
            
    mock_executor = MockExecutor()
    engine = CommunicationEngine(repository=None, reply_parser=None, executor=mock_executor)
    
    result = await engine.dispatch_action("AWB123", action)
    assert result is True
    assert mock_executor.executed is True

@pytest.mark.asyncio
async def test_communication_engine_legacy_fallback():
    """Test generic action categories do not imply Voice and retain existing behavior."""
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.HUMAN_ASSISTANCE,
        reasoning="Test",
        parameters={}
    )
    
    class MockExecutor:
        executed = False
        async def execute_engagement(self, action_request, **kwargs):
            self.executed = True
            
    mock_executor = MockExecutor()
    engine = CommunicationEngine(repository=None, reply_parser=None, executor=mock_executor)
    
    # Overwrite private method to test routing
    escalated = False
    async def mock_escalate(awb_no, act):
        nonlocal escalated
        escalated = True
        return True
        
    engine._trigger_concierge_escalation = mock_escalate
    
    result = await engine.dispatch_action("AWB123", action)
    assert result is True
    assert mock_executor.executed is False
    assert escalated is True

@pytest.mark.asyncio
async def test_executor_missing_credentials():
    """Test missing Exotel configuration fails safely in ExotelVoiceBotAdapter."""
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Test",
        parameters={"customer_phone": "+1234567890"},
        execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE)
    )
    
    adapter = ExotelVoiceBotAdapter()
    adapter.api_key = None  # Force failure
    
    with pytest.raises(ValueError, match="Exotel credentials or flow URL not fully configured."):
        await adapter.dispatch_call(action, "eng_123")

@pytest.mark.asyncio
async def test_communication_engine_unsupported_intent_fails():
    """Test that generic action categories without explicit intent fail rather than dropping silently."""
    action = ActionRequest(
        action_request_id="act_123",
        category=ActionCategory.AUTOMATED_RESPONSE,
        reasoning="Test",
        parameters={}
    )
    
    class MockExecutor:
        executed = False
        async def execute_engagement(self, action_request, **kwargs):
            self.executed = True
            
    mock_executor = MockExecutor()
    engine = CommunicationEngine(repository=None, reply_parser=None, executor=mock_executor)
    
    result = await engine.dispatch_action("AWB123", action)
    assert result is False
    assert mock_executor.executed is False
