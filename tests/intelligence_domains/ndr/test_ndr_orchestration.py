import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
import uuid

from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.intelligence_domains.ndr.models import (
    StrategyPatternType,
    DownstreamOutcomeSignal,
    RecoveryStrategy
)
from src.shared.cognitive_planning_contracts import (
    EvidencePackage,
    EvidenceItem,
    ProvenanceMetadata
)
from src.shared.conversational_contracts import (
    ConversationalUnderstanding,
    ConversationalIntent,
    ConversationalResponseType
)
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessRealityStatus
)
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.brain_core.action_engine.contracts import ActionCategory
from src.brain_core.gateway.interfaces import ModelGatewayProvider
from src.brain_core.knowledge.interfaces import KnowledgeProvider
from src.brain_core.memory.interfaces import MemoryProvider, MemoryEntry
from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.brain_core.classification.classifier import RequirementClassifier
from src.shared.rabta_interfaces import (
    IntelligenceDomainResolver,
    ContextExecutionResolver
)

@pytest.fixture
def mock_gateway():
    return AsyncMock(spec=ModelGatewayProvider)

@pytest.fixture
def mock_knowledge():
    k = AsyncMock(spec=KnowledgeProvider)
    k.search_knowledge.return_value = []
    return k

@pytest.fixture
def mock_memory():
    m = AsyncMock(spec=MemoryProvider)
    m.read_memory.return_value = []
    m.write_memory.return_value = None
    return m

@pytest.fixture
def mock_sql_engine():
    s = AsyncMock()
    s.generate_sql.return_value = "SELECT * FROM vw_shopdeck_shipment_ndr_reports WHERE awb_no = 'AWB12345';"
    return s

@pytest.fixture
def mock_azm_provider():
    a = MagicMock()
    a.get_namespace_schema.return_value = {
        "vw_shopdeck_shipment_ndr_reports": {
            "columns": {"awb_no": "STRING", "latest_ndr_reason": "STRING"}
        }
    }
    return a

@pytest.mark.asyncio
async def test_ndr_orchestrate_resolution_vertical_slice(mock_gateway, mock_knowledge, mock_memory):
    """
    Test Phase 3 & 4: Full vertical recovery slice from trigger signal to governed recommendation.
    """
    orchestrator = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=mock_knowledge,
        memory=mock_memory
    )

    evidence_pkg = EvidencePackage(
        package_id=str(uuid.uuid4()),
        plan_id=str(uuid.uuid4()),
        sufficiency_assessment="SUFFICIENT",
        evidence_items=[
            EvidenceItem(
                item_id=str(uuid.uuid4()),
                semantic_identity="ndr.event_payload",
                data_payload={
                    "ndr.entity.order_id": "ORD-9901",
                    "shopdeck.entity.order.gross_value": 1850.0,
                    "shopdeck.entity.payment.mode": "cod",
                    "shopdeck.metric.ndr_count": 1,
                    "shopdeck.event.delivery_exception.reason": "Customer unavailable / door locked",
                    "ndr.entity.courier_partner": "Delhivery",
                    "ndr.entity.customer_id": "cust_456",
                    "ndr.entity.customer": "Rahul Verma",
                    "customer.attribute.phone": "+919876543210",
                    "customer.attribute.preferred_date": "2026-09-04",
                    "customer.state.sentiment": "NEUTRAL",
                    "ndr.entity.awb": "AWB_DEL_7788"
                },
                provenance=ProvenanceMetadata(
                    source_system="urn:aarambooks:webhook:ndr",
                    retrieval_timestamp=datetime.now(UTC)
                )
            )
        ]
    )

    decision, action, customer_message = await orchestrator.orchestrate_resolution(evidence_pkg)

    # 1. Recovery Strategy Selected as first-class concept
    assert decision.recommended_alternative_id == StrategyPatternType.AUTONOMOUS_RESCHEDULE.value
    assert len(decision.alternatives_considered) == 1
    assert "Autonomous Rescheduling" in decision.justification

    # 2. Governed Action Request Formulated
    assert action is not None
    assert action.category == ActionCategory.SUGGESTED_RESOLUTION
    assert action.parameters.get("reattempt_date") == "2026-09-04"

    # 3. Customer message generated
    assert customer_message is not None
    assert "2026-09-04" in customer_message

    # 4. Case evidence saved to memory
    assert mock_memory.write_memory.call_count == 1
    call_args = mock_memory.write_memory.call_args
    assert "AWB_DEL_7788" in call_args[1]["session_id"]

@pytest.mark.asyncio
async def test_ndr_outcome_evaluation_and_learning_loop(mock_gateway, mock_knowledge, mock_memory):
    """
    Test Phase 8: Outcome Intelligence and Learning Loop recording real delivery outcome.
    """
    orchestrator = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=mock_knowledge,
        memory=mock_memory
    )

    strategy = RecoveryStrategy(
        strategy_type=StrategyPatternType.AUTONOMOUS_RESCHEDULE,
        strategy_name="Autonomous Reschedule",
        target_objective="Schedule reattempt",
        confidence=0.90,
        rationale="Customer agreed to date"
    )

    outcome_signal = DownstreamOutcomeSignal(
        awb_no="AWB_DEL_7788",
        order_status="delivered",
        execution_confirmed=True,
        customer_engaged=True,
        delivery_recovered=True,
        rto_avoided=True,
        is_final_rto=False
    )

    outcome, evidence = await orchestrator.evaluate_and_record_outcome(
        case_id="case_7788",
        awb_no="AWB_DEL_7788",
        strategy=strategy,
        signal=outcome_signal,
        order_value=1850.0
    )

    assert outcome.was_delivery_recovered is True
    assert outcome.was_rto_avoided is True
    assert outcome.revenue_protected == 1850.0
    assert outcome.freight_saved is None

    # Evidence written to memory
    assert mock_memory.write_memory.call_count == 1
    call_args = mock_memory.write_memory.call_args
    assert "ndr_learning_AWB_DEL_7788" in call_args[1]["session_id"]

@pytest.mark.asyncio
async def test_ndr_extract_understanding():
    """
    Test Phase 6: Rabta R-1 understanding and entity extraction.
    """
    orchestrator = NDRIntelligenceOrchestrator(
        gateway=AsyncMock(),
        knowledge=AsyncMock(),
        memory=AsyncMock()
    )

    understanding = await orchestrator.extract_understanding("What is the NDR status of AWB 9988776655?")
    assert understanding.intent == ConversationalIntent.RETRIEVE
    assert understanding.entities[0].original_expression == "9988776655"
    assert understanding.entities[0].inferred_type == "ndr.entity.awb"

    action_understanding = await orchestrator.extract_understanding("Please reschedule delivery for AWB 9988776655")
    assert action_understanding.intent == ConversationalIntent.ACTION

@pytest.mark.asyncio
async def test_ndr_rabta_end_to_end_conversational_routing(mock_gateway, mock_memory, mock_azm_provider):
    """
    Test Phase 7: Complete conversational query routing from Rabta Orchestrator to NDR-ID.
    """
    ndr_orch = NDRIntelligenceOrchestrator(
        gateway=mock_gateway,
        knowledge=AsyncMock(),
        memory=mock_memory,
        azm_provider=mock_azm_provider
    )
    
    mock_id_resolver = MagicMock(spec=IntelligenceDomainResolver)
    mock_id_resolver.resolve.side_effect = lambda urn: ndr_orch if urn == "urn:aarambooks:intelligence:ndr" else None
    
    from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
    mock_cem_adapter = AsyncMock()
    mock_cem_adapter.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        retrieved_evidence={"shipment_ndr_reports": [{"awb_no": "12345"}]}
    )
    mock_cem_resolver = MagicMock(spec=ContextExecutionResolver)
    mock_cem_resolver.resolve.return_value = mock_cem_adapter
    
    rabta = RabtaOrchestrator(
        id_resolver=mock_id_resolver,
        cem_resolver=mock_cem_resolver,
        classifier=RequirementClassifier(mock_gateway),
        memory_provider=mock_memory
    )
    
    query = "What is the NDR status of AWB 12345?"
    response = await rabta.process_query(
        query=query,
        id_urn="urn:aarambooks:intelligence:ndr",
        cem_urn="urn:aarambooks:cem:ndr",
        auth_context="test_auth",
        session_id="session_ndr_1"
    )
    
    assert response is not None
    assert response.response_type == ConversationalResponseType.SUCCESS
    assert "NDR shipment record located" in response.message
