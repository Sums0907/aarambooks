import pytest
from src.intelligence_domains.ndr.models import (
    NDRContext,
    FailureCategory,
    FailureDiagnosis,
    CustomerState,
    StrategyPatternType,
    DownstreamOutcomeSignal
)
from src.intelligence_domains.ndr.knowledge import (
    NDRDiagnosticEngine,
    NDRPriorityRiskEngine,
    NDRStrategyEngine,
    NDROutcomeEvaluator
)
from src.brain_core.action_engine.contracts import ActionCategory

def test_failure_diagnosis_categories():
    # 1. Unavailable
    diag1 = NDRDiagnosticEngine.diagnose_failure("Customer not available / door locked", "Delhivery", 1)
    assert diag1.category == FailureCategory.CUSTOMER_UNAVAILABLE
    assert diag1.is_carrier_disputed is False

    # 2. Fake Attempt
    diag2 = NDRDiagnosticEngine.diagnose_failure("Fake attempt / driver skipped address", "Delhivery", 1)
    assert diag2.category == FailureCategory.SUSPECTED_FAKE_ATTEMPT
    assert diag2.is_carrier_disputed is True

    # 3. Buyer Remorse / Rejection
    diag3 = NDRDiagnosticEngine.diagnose_failure("Customer refused OTP at doorstep", "Delhivery", 1)
    assert diag3.category == FailureCategory.BUYER_REMORSE_OR_REJECTION

    # 4. Address Defect
    diag4 = NDRDiagnosticEngine.diagnose_failure("Incomplete address, missing landmark", "Delhivery", 1)
    assert diag4.category == FailureCategory.ADDRESS_OR_LOCATION_DEFECT

def test_priority_and_risk_engine_dimensions():
    context = NDRContext(
        awb_no="AWB1001",
        courier_partner="Delhivery",
        payment_mode="cod",
        order_value=3500.0,
        attempt_count=1,
        latest_ndr_reason="Customer not available"
    )
    diagnosis = FailureDiagnosis(
        category=FailureCategory.CUSTOMER_UNAVAILABLE,
        root_cause_explanation="Customer unavailable",
        is_carrier_disputed=False
    )
    customer_state = CustomerState(sentiment="NEUTRAL")

    risk = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diagnosis, customer_state)

    # Operational risk, commercial priority, and CX risk are distinct
    assert 0.0 <= risk.operational_risk_score <= 1.0
    assert risk.commercial_priority_score == 0.80 # 3500 order value tier
    assert risk.customer_experience_risk_score == 0.30
    assert risk.policy_allows_autonomous_action is True

def test_commercial_priority_does_not_bypass_policy():
    """
    Boundary Test: High Commercial Priority ($10,000 order) must NOT bypass max attempt policy.
    """
    context = NDRContext(
        awb_no="AWB_VIP_999",
        courier_partner="Delhivery",
        payment_mode="cod",
        order_value=10000.0, # High commercial value
        attempt_count=3,     # Policy limit reached
        latest_ndr_reason="Customer unavailable"
    )
    diagnosis = FailureDiagnosis(
        category=FailureCategory.CUSTOMER_UNAVAILABLE,
        root_cause_explanation="Customer unavailable",
        is_carrier_disputed=False
    )
    risk = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diagnosis)

    assert risk.commercial_priority_score == 0.95
    # Max attempt policy strictly blocks autonomous action despite high commercial priority
    assert risk.policy_allows_autonomous_action is False
    assert "Max 3 autonomous reattempt policy reached" in risk.policy_constraint_notes

    strategy, recommendation = NDRStrategyEngine.determine_strategy(context, diagnosis, risk)
    # Must escalate to human concierge rather than autonomous reattempt
    assert strategy.strategy_type == StrategyPatternType.PRIORITY_CONCIERGE_ESCALATION
    assert recommendation.action_category == ActionCategory.HUMAN_ASSISTANCE
    assert recommendation.requires_human_approval is True

def test_candidate_strategy_patterns():
    context = NDRContext(
        awb_no="AWB2002",
        courier_partner="Delhivery",
        payment_mode="cod",
        order_value=1500.0,
        attempt_count=1,
        latest_ndr_reason="Customer unavailable"
    )
    customer_state = CustomerState(preferred_reattempt_date="2026-09-05")

    # 1. Customer Unavailable -> Autonomous Reschedule
    diag1 = FailureDiagnosis(category=FailureCategory.CUSTOMER_UNAVAILABLE, root_cause_explanation="unavailable")
    risk1 = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diag1, customer_state)
    strat1, rec1 = NDRStrategyEngine.determine_strategy(context, diag1, risk1, customer_state)
    assert strat1.strategy_type == StrategyPatternType.AUTONOMOUS_RESCHEDULE
    assert rec1.parameters.get("reattempt_date") == "2026-09-05"

    # 2. Suspected Fake Attempt -> Dispute Courier
    diag2 = FailureDiagnosis(category=FailureCategory.SUSPECTED_FAKE_ATTEMPT, root_cause_explanation="fake attempt", is_carrier_disputed=True)
    risk2 = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diag2)
    strat2, rec2 = NDRStrategyEngine.determine_strategy(context, diag2, risk2)
    assert strat2.strategy_type == StrategyPatternType.DOORSTEP_VERIFICATION_AND_DISPUTE
    assert rec2.action_type == "courier_dispute"

    # 3. Buyer Remorse -> Prepayment Incentive
    diag3 = FailureDiagnosis(category=FailureCategory.BUYER_REMORSE_OR_REJECTION, root_cause_explanation="remorse")
    risk3 = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diag3)
    strat3, rec3 = NDRStrategyEngine.determine_strategy(context, diag3, risk3)
    assert strat3.strategy_type == StrategyPatternType.BUYER_COMMITMENT_AND_PREPAYMENT
    assert rec3.action_type == "offer_prepayment_incentive"

    # 4. Address Defect -> Address Enrichment
    diag4 = FailureDiagnosis(category=FailureCategory.ADDRESS_OR_LOCATION_DEFECT, root_cause_explanation="missing landmark")
    risk4 = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diag4)
    strat4, rec4 = NDRStrategyEngine.determine_strategy(context, diag4, risk4)
    assert strat4.strategy_type == StrategyPatternType.ADDRESS_AND_LANDMARK_ENRICHMENT
    assert rec4.action_type == "address_enrichment_request"

def test_outcome_evaluator_distinctions():
    """
    Boundary Test: Action Executed != Delivery Recovered != RTO Avoided
    """
    from src.intelligence_domains.ndr.models import RecoveryStrategy
    strategy = RecoveryStrategy(
        strategy_type=StrategyPatternType.AUTONOMOUS_RESCHEDULE,
        strategy_name="Autonomous Reschedule",
        target_objective="Schedule reattempt",
        confidence=0.9,
        rationale="Scheduled reattempt"
    )

    # Scenario A: Action executed, but customer was unavailable and parcel RTO'd
    signal_failed = DownstreamOutcomeSignal(
        awb_no="AWB_FAIL",
        order_status="rto_delivered",
        execution_confirmed=True,
        customer_engaged=True,
        delivery_recovered=False,
        rto_avoided=False,
        is_final_rto=True
    )
    outcome_failed, evidence_failed = NDROutcomeEvaluator.evaluate_outcome(
        case_id="case_1",
        awb_no="AWB_FAIL",
        strategy=strategy,
        signal=signal_failed,
        order_value=2500.0
    )
    assert outcome_failed.was_action_executed is True
    assert outcome_failed.was_delivery_recovered is False
    assert outcome_failed.was_rto_avoided is False
    assert outcome_failed.revenue_protected == 0.0

    # Scenario B: Action executed, and parcel successfully delivered!
    signal_success = DownstreamOutcomeSignal(
        awb_no="AWB_SUCCESS",
        order_status="delivered",
        execution_confirmed=True,
        customer_engaged=True,
        delivery_recovered=True,
        rto_avoided=True,
        is_final_rto=False
    )
    outcome_success, evidence_success = NDROutcomeEvaluator.evaluate_outcome(
        case_id="case_2",
        awb_no="AWB_SUCCESS",
        strategy=strategy,
        signal=signal_success,
        order_value=2500.0
    )
    assert outcome_success.was_delivery_recovered is True
    assert outcome_success.was_rto_avoided is True
    assert outcome_success.revenue_protected == 2500.0
    assert outcome_success.freight_saved == 120.0
