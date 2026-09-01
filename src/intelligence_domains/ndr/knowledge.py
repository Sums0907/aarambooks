from typing import Optional, Dict, Any, List
import uuid
from src.intelligence_domains.ndr.models import (
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
    LearningEvidence
)
from src.brain_core.action_engine.contracts import ActionCategory

class NDRDiagnosticEngine:
    """
    Diagnoses root causes of delivery failures by mapping raw courier exception strings
    and event contexts into canonical semantic failure modes.
    """
    @staticmethod
    def diagnose_failure(reason_text: str, courier_partner: str, attempt_count: int) -> FailureDiagnosis:
        normalized = (reason_text or "").lower().strip()
        
        # 1. Suspected Courier Fake Attempt / Driver Skip
        if any(term in normalized for term in ["fake", "no visit", "driver skip", "unattempted", "false scan"]) or (
            courier_partner.lower() in ["shadowfax", "delhivery"] and "not reachable" in normalized and attempt_count == 1
        ):
            return FailureDiagnosis(
                category=FailureCategory.SUSPECTED_FAKE_ATTEMPT,
                root_cause_explanation="Potential false exception scan where courier driver skipped physical doorstep verification.",
                is_carrier_disputed=True,
                confidence=0.75
            )

        # 2. Buyer Remorse / Rejection / OTP Refusal
        if any(term in normalized for term in ["otp", "refused", "rejected", "cancel", "remorse", "not interested", "price"]):
            return FailureDiagnosis(
                category=FailureCategory.BUYER_REMORSE_OR_REJECTION,
                root_cause_explanation="Recipient declined OTP verification, expressed buyer remorse, or rejected COD doorstep payment.",
                is_carrier_disputed=False,
                confidence=0.90
            )

        # 3. Address / Location Defect
        if any(term in normalized for term in ["address", "incomplete", "landmark", "pincode", "wrong address", "untraceable", "location"]):
            return FailureDiagnosis(
                category=FailureCategory.ADDRESS_OR_LOCATION_DEFECT,
                root_cause_explanation="Courier reported an incomplete, incorrect, or untraceable delivery address or missing landmark.",
                is_carrier_disputed=False,
                confidence=0.85
            )

        # 4. Customer Unavailable / Scheduling
        if any(term in normalized for term in ["unavailable", "not reachable", "door locked", "out of station", "rescheduled", "future date", "customer not available", "call not answered"]):
            return FailureDiagnosis(
                category=FailureCategory.CUSTOMER_UNAVAILABLE,
                root_cause_explanation="Customer was temporarily unreachable, door was locked, or delivery requested for a later date.",
                is_carrier_disputed=False,
                confidence=0.90
            )

        # 5. Operational / Transit Delay
        if any(term in normalized for term in ["vehicle", "weather", "operational", "strike", "entry restricted", "hub delay"]):
            return FailureDiagnosis(
                category=FailureCategory.OPERATIONAL_OR_TRANSIT_DELAY,
                root_cause_explanation="Logistics operational disruption, weather issue, or vehicle delay outside customer control.",
                is_carrier_disputed=False,
                confidence=0.80
            )

        return FailureDiagnosis(
            category=FailureCategory.UNKNOWN,
            root_cause_explanation=f"Unclassified exception: {reason_text}",
            is_carrier_disputed=False,
            confidence=0.50
        )


class NDRPriorityRiskEngine:
    """
    Evaluates Operational Risk, Commercial Priority, and Customer Experience Risk as distinct dimensions.
    Enforces Policy Supremacy: High commercial priority NEVER bypasses business policies.
    """
    @staticmethod
    def evaluate_priority_and_risk(
        context: NDRContext,
        diagnosis: FailureDiagnosis,
        customer_state: Optional[CustomerState] = None
    ) -> PriorityAndRiskEvaluation:
        # 1. Operational Risk (0.0 to 1.0)
        # Driven by attempt degradation, payment exposure (COD is higher risk), and failure category
        base_risk = 0.3 * min(context.attempt_count, 3)
        if context.payment_mode.lower() == "cod":
            base_risk += 0.2
        if diagnosis.category == FailureCategory.BUYER_REMORSE_OR_REJECTION:
            base_risk += 0.25
        elif diagnosis.category == FailureCategory.CUSTOMER_UNAVAILABLE:
            base_risk += 0.1
        operational_risk = min(1.0, max(0.1, base_risk))

        # 2. Commercial Priority (0.0 to 1.0)
        # Driven by financial value
        if context.order_value >= 5000:
            commercial_priority = 0.95
        elif context.order_value >= 2500:
            commercial_priority = 0.80
        elif context.order_value >= 1000:
            commercial_priority = 0.50
        else:
            commercial_priority = 0.25

        # 3. Customer Experience Risk (0.0 to 1.0)
        # Driven by customer distress, dispute state, and attempt friction
        sentiment = customer_state.sentiment.upper() if customer_state else "NEUTRAL"
        if sentiment in ["FRUSTRATED", "HOSTILE"]:
            cx_risk = 0.90
        elif diagnosis.is_carrier_disputed:
            cx_risk = 0.75
        elif context.attempt_count >= 2:
            cx_risk = 0.60
        else:
            cx_risk = 0.30

        # RTO Probability & Recovery Probability
        rto_prob = min(0.95, operational_risk * 0.8 + (0.2 if sentiment in ["FRUSTRATED", "HOSTILE"] else 0.0))
        recovery_prob = max(0.05, 1.0 - rto_prob)

        # Policy Constraint Check (Max 3 reattempts standard policy)
        policy_allows_autonomous = True
        policy_notes = None
        if context.attempt_count >= 3:
            policy_allows_autonomous = False
            policy_notes = "Max 3 autonomous reattempt policy reached. Requires human supervisor review."

        return PriorityAndRiskEvaluation(
            operational_risk_score=round(operational_risk, 2),
            commercial_priority_score=round(commercial_priority, 2),
            customer_experience_risk_score=round(cx_risk, 2),
            rto_probability=round(rto_prob, 2),
            recovery_probability=round(recovery_prob, 2),
            policy_allows_autonomous_action=policy_allows_autonomous,
            policy_constraint_notes=policy_notes
        )


class NDRStrategyEngine:
    """
    Formulates candidate recovery strategy and intervention recommendation based on multi-factor context.
    """
    @staticmethod
    def determine_strategy(
        context: NDRContext,
        diagnosis: FailureDiagnosis,
        risk: PriorityAndRiskEvaluation,
        customer_state: Optional[CustomerState] = None
    ) -> tuple[RecoveryStrategy, InterventionRecommendation]:
        
        rec_id = f"rec_{uuid.uuid4().hex[:8]}"

        # Rule 1: Policy Boundary or Terminal Attempt ➔ Concierge Escalation
        if not risk.policy_allows_autonomous_action or risk.customer_experience_risk_score >= 0.85:
            strategy = RecoveryStrategy(
                strategy_type=StrategyPatternType.PRIORITY_CONCIERGE_ESCALATION,
                strategy_name="Priority Concierge Escalation",
                target_objective="Transfer case context to human care desk for high-touch intervention.",
                parameters={"awb_no": context.awb_no, "urgency": "HIGH", "order_value": context.order_value},
                confidence=0.95,
                rationale="High customer distress or policy threshold reached; autonomous resolution halted."
            )
            recommendation = InterventionRecommendation(
                recommendation_id=rec_id,
                action_type="concierge_escalate",
                action_category=ActionCategory.HUMAN_ASSISTANCE,
                parameters={"awb_no": context.awb_no, "reason": risk.policy_constraint_notes or "High CX Risk"},
                justification="Case requires human concierge triage.",
                customer_message="We've assigned a dedicated delivery specialist to assist you personally.",
                requires_human_approval=True
            )
            return strategy, recommendation

        # Rule 2: Suspected Fake Attempt ➔ Doorstep Verification & Carrier Dispute
        if diagnosis.category == FailureCategory.SUSPECTED_FAKE_ATTEMPT:
            strategy = RecoveryStrategy(
                strategy_type=StrategyPatternType.DOORSTEP_VERIFICATION_AND_DISPUTE,
                strategy_name="Doorstep Verification & Carrier Dispute",
                target_objective="Verify customer doorstep status and file carrier dispute.",
                parameters={"courier": context.courier_partner, "awb_no": context.awb_no},
                confidence=0.88,
                rationale="Suspected fake attempt scan detected; carrier verification required."
            )
            recommendation = InterventionRecommendation(
                recommendation_id=rec_id,
                action_type="courier_dispute",
                action_category=ActionCategory.SUGGESTED_RESOLUTION,
                parameters={"awb_no": context.awb_no, "dispute_reason": "UNVISITED_DOORSTEP_SKIP"},
                justification="Recommending carrier dispute and priority reattempt.",
                customer_message="We noticed an issue with your delivery attempt. We are coordinating with courier management to force a reattempt.",
                requires_human_approval=False
            )
            return strategy, recommendation

        # Rule 3: Address / Location Defect ➔ Address Enrichment
        if diagnosis.category == FailureCategory.ADDRESS_OR_LOCATION_DEFECT:
            strategy = RecoveryStrategy(
                strategy_type=StrategyPatternType.ADDRESS_AND_LANDMARK_ENRICHMENT,
                strategy_name="Address & Landmark Enrichment",
                target_objective="Obtain clear landmark or alternate contact to fix delivery defect.",
                parameters={"awb_no": context.awb_no},
                confidence=0.85,
                rationale="Incomplete address reported; enrichment required before reattempt."
            )
            recommendation = InterventionRecommendation(
                recommendation_id=rec_id,
                action_type="address_enrichment_request",
                action_category=ActionCategory.AUTOMATED_RESPONSE,
                parameters={"awb_no": context.awb_no, "enrichment_type": "LANDMARK_REQUIRED"},
                justification="Requesting customer landmark to ensure successful doorstep routing.",
                customer_message="Your courier could not locate your address. Please provide a nearby landmark.",
                requires_human_approval=False
            )
            return strategy, recommendation

        # Rule 4: Buyer Remorse / COD Rejection ➔ Buyer Commitment & Prepayment
        if diagnosis.category == FailureCategory.BUYER_REMORSE_OR_REJECTION:
            strategy = RecoveryStrategy(
                strategy_type=StrategyPatternType.BUYER_COMMITMENT_AND_PREPAYMENT,
                strategy_name="Buyer Commitment & Prepayment Conversion",
                target_objective="Convert COD to instant digital prepaid or confirm genuine intent.",
                parameters={"awb_no": context.awb_no, "payment_mode": context.payment_mode},
                confidence=0.82,
                rationale="Buyer hesitation detected; prepayment incentive recommended."
            )
            recommendation = InterventionRecommendation(
                recommendation_id=rec_id,
                action_type="offer_prepayment_incentive",
                action_category=ActionCategory.RECOMMENDATION,
                parameters={"awb_no": context.awb_no, "discount_percentage": 5.0},
                justification="Offering verified prepayment link with 5% instant discount to eliminate COD refusal.",
                customer_message="Would you like to complete payment online to enjoy guaranteed contactless delivery and 5% instant savings?",
                requires_human_approval=False
            )
            return strategy, recommendation

        # Rule 5: Default Customer Unavailable ➔ Autonomous Rescheduling (Playbook A)
        strategy = RecoveryStrategy(
            strategy_type=StrategyPatternType.AUTONOMOUS_RESCHEDULE,
            strategy_name="Autonomous Rescheduling",
            target_objective="Capture firm customer reattempt date and schedule with courier.",
            parameters={"awb_no": context.awb_no, "attempt_count": context.attempt_count},
            confidence=0.90,
            rationale="Customer temporarily unavailable; scheduled reattempt is optimal."
        )
        target_date = customer_state.preferred_reattempt_date if (customer_state and customer_state.preferred_reattempt_date) else "NEXT_BUSINESS_DAY"
        recommendation = InterventionRecommendation(
            recommendation_id=rec_id,
            action_type="seller_reattempt",
            action_category=ActionCategory.SUGGESTED_RESOLUTION,
            parameters={"awb_no": context.awb_no, "reattempt_date": target_date},
            justification=f"Recommending reattempt on {target_date} based on customer availability.",
            customer_message=f"We noticed you were unavailable. We have requested delivery reattempt for {target_date}.",
            requires_human_approval=False
        )
        return strategy, recommendation


class NDROutcomeEvaluator:
    """
    Evaluates physical downstream delivery outcomes against strategy predictions.
    Enforces the outcome chain: Recommendation != Execution != Engagement != Delivery Recovery != RTO Avoided.
    """
    @staticmethod
    def evaluate_outcome(
        case_id: str,
        awb_no: str,
        strategy: RecoveryStrategy,
        signal: DownstreamOutcomeSignal,
        order_value: float = 0.0
    ) -> tuple[OutcomeEvaluation, LearningEvidence]:
        
        is_recovered = signal.delivery_recovered and (signal.order_status.lower() in ["delivered", "complete"])
        is_rto = signal.is_final_rto or (signal.order_status.lower() in ["rto_initiated", "rto_delivered", "returned"])

        revenue_protected = order_value if is_recovered else 0.0
        freight_saved = 120.0 if is_recovered else 0.0 # Estimated 2-way reverse logistics fee avoided

        summary = (
            f"Case {case_id} (AWB: {awb_no}) evaluated. "
            f"Strategy: {strategy.strategy_type.value}. "
            f"Executed: {signal.execution_confirmed}, Engaged: {signal.customer_engaged}, "
            f"Delivered: {is_recovered}, RTO: {is_rto}."
        )

        outcome = OutcomeEvaluation(
            case_id=case_id,
            awb_no=awb_no,
            strategy_attempted=strategy.strategy_type,
            was_recommendation_accepted=True,
            was_action_executed=signal.execution_confirmed,
            was_customer_engaged=signal.customer_engaged,
            was_delivery_recovered=is_recovered,
            was_rto_avoided=not is_rto,
            revenue_protected=revenue_protected,
            freight_saved=freight_saved,
            evaluation_summary=summary
        )

        evidence = LearningEvidence(
            case_id=case_id,
            awb_no=awb_no,
            courier_partner=strategy.parameters.get("courier", "unknown"),
            failure_category=FailureCategory.UNKNOWN,
            strategy_used=strategy.strategy_type,
            recovered=is_recovered,
            evidence_text=summary
        )

        return outcome, evidence
