import pytest
from datetime import datetime, UTC
from src.intelligence_domains.ndr.models import (
    NDRCase,
    NDREvent,
    NDRContext,
    FailureCategory,
    FailureDiagnosis,
    CustomerState,
    PriorityAndRiskEvaluation,
    StrategyPatternType,
    RecoveryStrategy,
    InterventionRecommendation,
    DownstreamOutcomeSignal,
    OutcomeEvaluation,
    LearningEvidence,
    CaseLifecycleState
)
from src.brain_core.action_engine.contracts import ActionCategory

def test_ndr_event_instantiation():
    event = NDREvent(
        awb_no="AWB99887766",
        courier_partner="Delhivery",
        failure_code="CUST_UNAVAIL",
        failure_description="Customer unavailable at doorstep",
        attempt_count=1
    )
    assert event.awb_no == "AWB99887766"
    assert event.attempt_count == 1
    assert event.courier_partner == "Delhivery"

def test_priority_and_risk_evaluation_bounds():
    risk = PriorityAndRiskEvaluation(
        operational_risk_score=0.45,
        commercial_priority_score=0.90,
        customer_experience_risk_score=0.30,
        rto_probability=0.40,
        recovery_probability=0.60,
        policy_allows_autonomous_action=True
    )
    assert risk.operational_risk_score == 0.45
    assert risk.commercial_priority_score == 0.90
    assert risk.policy_allows_autonomous_action is True

def test_recovery_strategy_and_recommendation_link():
    strat = RecoveryStrategy(
        strategy_type=StrategyPatternType.AUTONOMOUS_RESCHEDULE,
        strategy_name="Autonomous Reschedule",
        target_objective="Schedule reattempt",
        parameters={"reattempt_date": "2026-09-03"},
        confidence=0.92,
        rationale="Customer temporarily unavailable"
    )
    rec = InterventionRecommendation(
        recommendation_id="rec_123",
        action_type="seller_reattempt",
        action_category=ActionCategory.SUGGESTED_RESOLUTION,
        parameters={"awb_no": "AWB123", "date": "2026-09-03"},
        justification="Reattempt approved"
    )
    assert strat.strategy_type == StrategyPatternType.AUTONOMOUS_RESCHEDULE
    assert rec.action_category == ActionCategory.SUGGESTED_RESOLUTION
    assert rec.requires_human_approval is False

def test_outcome_chain_separation():
    signal = DownstreamOutcomeSignal(
        awb_no="AWB123",
        order_status="Delivered",
        execution_confirmed=True,
        customer_engaged=True,
        delivery_recovered=True,
        rto_avoided=True,
        is_final_rto=False
    )
    assert signal.delivery_recovered is True
    assert signal.rto_avoided is True
    assert signal.is_final_rto is False
