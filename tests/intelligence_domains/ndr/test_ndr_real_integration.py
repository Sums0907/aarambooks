import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
import uuid

from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.intelligence_domains.ndr.knowledge import NDRDiagnosticEngine, NDRPriorityRiskEngine, NDRStrategyEngine, NDROutcomeEvaluator
from src.intelligence_domains.ndr.models import NDREvent, NDRContext, FailureCategory, PriorityAndRiskEvaluation, StrategyPatternType
from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.brain_core.classification.classifier import RequirementClassifier
from src.brain_core.gateway.interfaces import ModelGatewayProvider
from src.brain_core.memory.interfaces import MemoryProvider
from src.shared.conversational_contracts import ConversationalResponse, ConversationalResponseType
from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessEvidenceResponse, BusinessRealityStatus

@pytest.fixture
def mock_gateway():
    gateway = AsyncMock(spec=ModelGatewayProvider)
    # Configure mock responses for integration path
    gateway.generate.return_value = MagicMock(content="Mocked response for integration test")
    return gateway

@pytest.fixture
def mock_memory():
    memory = AsyncMock(spec=MemoryProvider)
    return memory

@pytest.fixture
def mock_sql_engine():
    engine = AsyncMock()
    # Simulate a SQL query that retrieves fake attempt from ShopDeck
    engine.generate_sql.return_value = "SELECT * FROM vw_shopdeck_shipment_ndr_reports WHERE awb_no = 'AWB_TEST_REAL_1'"
    return engine

@pytest.fixture
def mock_azm_provider():
    azm = MagicMock()
    # Simulate the real schema
    azm.get_namespace_schema.return_value = {
        "vw_shopdeck_shipment_ndr_reports": {
            "columns": {
                "awb_no": "STRING",
                "order_status": "STRING",
                "latest_ndr_reason": "STRING",
                "ndr_count": "INTEGER"
            }
        }
    }
    return azm

@pytest.mark.asyncio
async def test_real_ndr_query_path(mock_gateway, mock_memory, mock_sql_engine, mock_azm_provider):
    """
    Test Phase 3: Trace a conversational NDR request through the real Rabta architecture 
    to the NDR-ID read substrate mapping to the ShopDeck business truth.
    """
    ndr_orch = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=AsyncMock(),
        memory=mock_memory,
        sql_engine=mock_sql_engine,
        azm_provider=mock_azm_provider
    )
    
    mock_id_resolver = MagicMock()
    mock_id_resolver.resolve.side_effect = lambda urn: ndr_orch if urn == "urn:aarambooks:intelligence:ndr" else None

    rabta = RabtaOrchestrator(
        id_resolver=mock_id_resolver,
        cem_resolver=MagicMock(),
        classifier=RequirementClassifier(mock_gateway),
        memory_provider=mock_memory
    )
    
    # Send a query
    query = "What is the NDR status of AWB 12345?"
    response = await rabta.process_query(
        query=query,
        id_urn="urn:aarambooks:intelligence:ndr",
        cem_urn="urn:aarambooks:cem:ndr",
        auth_context="test_auth",
        session_id="session_1"
    )
    
    assert response is not None
    # We verify the query path did invoke the expected orchestration chain.
    assert response.response_type == ConversationalResponseType.SUCCESS
    assert "NDR record retrieved" in response.message or "NDR shipment record located" in response.message

@pytest.mark.asyncio
async def test_real_event_path_and_governance(mock_gateway, mock_memory):
    """
    Test Phase 4 & 8: Trace a ShopDeck logistic event through NDR-ID engines 
    and verify policy governance (e.g. 3-attempt limit override).
    """
    # Event definition representing a policy-constrained case (3 attempts)
    event = NDREvent(
        event_id=str(uuid.uuid4()),
        awb_no="AWB_MAX_ATTEMPTS",
        order_id="ORD-99",
        courier_partner="Delhivery",
        attempt_count=3,
        failure_code="door_locked",
        failure_description="Customer unavailable / door locked",
        event_timestamp=datetime.now(UTC)
    )
    
    context = NDRContext(
        awb_no="AWB_MAX_ATTEMPTS",
        courier_partner="Delhivery",
        order_value=50000.0,  # High commercial priority
        payment_mode="cod",
        customer_id="cust_high_value",
        customer_name="High Value Cust",
        attempt_count=3
    )
    
    # 1. Diagnosis
    diagnosis = NDRDiagnosticEngine.diagnose_failure(
        event.failure_description, event.courier_partner, event.attempt_count
    )
    assert diagnosis.category == FailureCategory.CUSTOMER_UNAVAILABLE
    
    # 2. Risk & Priority
    evaluation = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diagnosis)
    
    # Governance Check: Even though it's high value, policy limits to 3 attempts,
    # so policy override should enforce escalation or limit automatic action.
    assert evaluation.commercial_priority_score >= 0.8
    assert evaluation.policy_allows_autonomous_action is False
    assert "Max 3 autonomous reattempt policy reached" in evaluation.policy_constraint_notes

    # 3. Strategy
    strategy, rec = NDRStrategyEngine.determine_strategy(context, diagnosis, evaluation)
    
    # Given policy escalation, strategy should be PRIORITY_CONCIERGE_ESCALATION or similar manual path
    assert strategy.strategy_type == StrategyPatternType.PRIORITY_CONCIERGE_ESCALATION

@pytest.mark.asyncio
async def test_outcome_path_and_business_value():
    """
    Test Phase 5 & 6: Validate the Outcome Path distinctions:
    Recommendation != Execution != Customer Engagement != Delivery Recovery != RTO Avoided
    """
    from src.intelligence_domains.ndr.models import RecoveryStrategy, DownstreamOutcomeSignal
    strategy_mock = RecoveryStrategy(
        strategy_type=StrategyPatternType.AUTONOMOUS_RESCHEDULE, 
        strategy_name="Reschedule", 
        target_objective="Recover", 
        confidence=0.8, 
        rationale="Mock"
    )

    # Scenario: Strategy recommended Reschedule, it was Executed, but Customer didn't respond
    signal_no_response = DownstreamOutcomeSignal(
        awb_no="AWB_1", execution_confirmed=True, customer_engaged=False, delivery_recovered=False, is_final_rto=True, order_status="RTO_INITIATED"
    )
    outcome, _ = NDROutcomeEvaluator.evaluate_outcome(
        case_id="case_1", awb_no="AWB_1", strategy=strategy_mock, signal=signal_no_response, order_value=2000.0
    )
    
    assert outcome.was_action_executed is True
    assert outcome.was_customer_engaged is False
    assert outcome.was_delivery_recovered is False
    assert outcome.was_rto_avoided is False
    assert outcome.freight_saved == 0.0
    
    # Scenario: Delivery recovered successfully
    signal_success = DownstreamOutcomeSignal(
        awb_no="AWB_1", execution_confirmed=True, customer_engaged=True, delivery_recovered=True, is_final_rto=False, order_status="DELIVERED"
    )
    outcome_success, _ = NDROutcomeEvaluator.evaluate_outcome(
        case_id="case_2", awb_no="AWB_1", strategy=strategy_mock, signal=signal_success, order_value=2000.0
    )
    
    assert outcome_success.was_action_executed is True
    assert outcome_success.was_customer_engaged is True
    assert outcome_success.was_delivery_recovered is True
    assert outcome_success.was_rto_avoided is True
    assert outcome_success.revenue_protected == 2000.0
    assert outcome_success.freight_saved > 0.0
