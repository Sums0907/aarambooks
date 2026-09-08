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
from src.brain_core.action_engine.contracts import ActionCategory, ExecutionIntent, ExecutionChannel

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
        safe_attempt_count = context.attempt_count if context.attempt_count is not None else 1
        base_risk = 0.3 * min(safe_attempt_count, 3)
        payment_penalty = 0.2 if context.payment_mode and context.payment_mode.lower() == "cod" else 0.0
        
        operational_risk = min(base_risk + payment_penalty, 1.0)

        # 2. Commercial Priority (0.0 to 1.0)
        # Driven by order value tiers and margin protection requirements
        safe_order_value = context.order_value if context.order_value is not None else 0.0
        if safe_order_value >= 5000:
            commercial_priority = 0.95
        elif safe_order_value >= 2500:
            commercial_priority = 0.80
        elif safe_order_value >= 1000:
            commercial_priority = 0.50
        else:
            commercial_priority = 0.25

        # 3. CX Risk Score (0.0 to 1.0)
        base_cx_risk = 0.30
        if safe_attempt_count >= 2:
            base_cx_risk = 0.60
        
        sentiment = customer_state.sentiment.upper() if customer_state else "NEUTRAL"
        sentiment_penalty = 0.4 if sentiment in ["FRUSTRATED", "HOSTILE", "NEGATIVE"] else 0.0
        cx_risk = min(base_cx_risk + sentiment_penalty, 1.0)

        # RTO Probability & Recovery Probability
        rto_prob = min(0.95, operational_risk * 0.8 + (0.2 if sentiment in ["FRUSTRATED", "HOSTILE"] else 0.0))
        recovery_prob = max(0.05, 1.0 - rto_prob)

        # Policy Constraint Check (Max 3 reattempts standard policy)
        policy_allows_autonomous = True
        policy_notes = None
        if safe_attempt_count >= 3:
            policy_allows_autonomous = False
            policy_notes = "3rd+ NDR attempt: no NDR recovery call is placed for this attempt, per policy."

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
        # Policy constraints always supersede commercial priority.
        if not risk.policy_allows_autonomous_action or risk.customer_experience_risk_score >= 0.85:
            strategy = RecoveryStrategy(
                strategy_type=StrategyPatternType.PRIORITY_CONCIERGE_ESCALATION,
                strategy_name="Priority Concierge Escalation",
                target_objective="Transfer case context to human care desk for high-touch intervention.",
                parameters={"awb_no": context.awb_no, "urgency": "HIGH", "order_value": context.order_value if context.order_value is not None else "UNKNOWN"},
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
                parameters={"courier": context.courier_partner if context.courier_partner else "UNKNOWN", "awb_no": context.awb_no},
                confidence=0.88,
                rationale="Suspected fake attempt scan detected; carrier verification required."
            )
            recommendation = InterventionRecommendation(
                recommendation_id=rec_id,
                action_type="courier_dispute",
                action_category=ActionCategory.SUGGESTED_RESOLUTION,
                parameters={"awb_no": context.awb_no, "dispute_reason": "UNVISITED_DOORSTEP_SKIP"},
                execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
                justification="Recommending carrier dispute and priority reattempt.",
                customer_message="We noticed an issue with your delivery attempt. Could you confirm whether someone was available at the address?",
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
                execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
                justification="Requesting customer landmark to ensure successful doorstep routing.",
                customer_message="Your courier could not locate your address. Please provide a nearby landmark.",
                requires_human_approval=False
            )
            return strategy, recommendation

        # Rule 4: Buyer Remorse / COD Rejection ➔ Buyer Intent Confirmation
        if diagnosis.category == FailureCategory.BUYER_REMORSE_OR_REJECTION:
            strategy = RecoveryStrategy(
                strategy_type=StrategyPatternType.BUYER_INTENT_CONFIRMATION,
                strategy_name="Buyer Intent Confirmation",
                target_objective="Confirm if the buyer still genuinely intends to receive the COD order.",
                parameters={"awb_no": context.awb_no},
                confidence=0.82,
                rationale="Buyer hesitation detected; need to confirm intent before reattempting."
            )
            recommendation = InterventionRecommendation(
                recommendation_id=rec_id,
                action_type="confirm_intent_to_receive",
                action_category=ActionCategory.RECOMMENDATION,
                parameters={"awb_no": context.awb_no},
                execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
                justification="Asking the customer to confirm their intent to receive the order.",
                customer_message="We noticed your order delivery was not completed. Would you still like us to deliver this order?",
                requires_human_approval=False
            )
            return strategy, recommendation

        # Rule 5: Default Customer Unavailable ➔ Autonomous Rescheduling (Playbook A)
        strategy = RecoveryStrategy(
            strategy_type=StrategyPatternType.AUTONOMOUS_RESCHEDULE,
            strategy_name="Autonomous Rescheduling",
            target_objective="Capture the customer's firm delivery preference for a human/ShopDeck BS to act on. Brain does not schedule with the courier directly.",
            parameters={"awb_no": context.awb_no, "attempt_count": context.attempt_count if context.attempt_count is not None else "UNKNOWN"},
            confidence=0.90,
            rationale="Customer temporarily unavailable; scheduled reattempt is optimal."
        )
        
        target_date = customer_state.preferred_reattempt_date if (customer_state and customer_state.preferred_reattempt_date) else "UNKNOWN_DATE"
        
        if target_date == "UNKNOWN_DATE":
            justification = "Recommending reattempt based on customer availability, date pending."
            customer_message = "We noticed you were unavailable. When would you like us to reattempt delivery?"
        else:
            justification = f"Recommending reattempt on {target_date} based on customer availability."
            customer_message = f"We noticed you were unavailable. We'll note {target_date} as your preferred reattempt date."
            
        recommendation = InterventionRecommendation(
            recommendation_id=rec_id,
            action_type="seller_reattempt",
            action_category=ActionCategory.SUGGESTED_RESOLUTION,
            parameters={"awb_no": context.awb_no, "reattempt_date": target_date, "customer_phone": context.customer_phone},
            execution_intent=ExecutionIntent(intent_type="CUSTOMER_OUTREACH", channel=ExecutionChannel.VOICE),
            justification=justification,
            customer_message=customer_message,
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
        diagnosis: Optional[FailureDiagnosis] = None,
        order_value: Optional[float] = None
    ) -> tuple[OutcomeEvaluation, LearningEvidence]:
        
        is_recovered = signal.delivery_recovered if signal.delivery_recovered is not None else None
        if is_recovered is None and signal.order_status:
            if signal.order_status.lower() in ["delivered", "complete"]:
                is_recovered = True
            elif signal.order_status.lower() in ["rto_initiated", "rto_delivered", "returned", "cancelled"]:
                is_recovered = False

        is_rto = signal.is_final_rto if signal.is_final_rto is not None else None
        if is_rto is None and signal.order_status:
            if signal.order_status.lower() in ["rto_initiated", "rto_delivered", "returned"]:
                is_rto = True
            elif signal.order_status.lower() in ["delivered", "complete"]:
                is_rto = False

        revenue_protected = None
        if is_recovered is True and order_value is not None:
            revenue_protected = order_value
            
        freight_saved = None
        # Freight savings require an explicitly approved business rule or evidence.
        # We cannot calculate it blindly from order_value or constant 120.0 without evidence.

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
            was_recommendation_accepted=None, # Cannot infer from mere execution
            was_action_executed=signal.execution_confirmed,
            was_customer_engaged=signal.customer_engaged,
            was_delivery_recovered=is_recovered,
            was_rto_avoided=False if is_rto is True else (True if is_rto is False else None),
            revenue_protected=revenue_protected,
            freight_saved=freight_saved,
            evaluation_summary=summary
        )

        evidence = LearningEvidence(
            case_id=case_id,
            awb_no=awb_no,
            courier_partner=strategy.parameters.get("courier"),
            failure_category=diagnosis.category if diagnosis else None,
            strategy_used=strategy.strategy_type,
            recovered=is_recovered,
            evidence_text=summary
        )

        return outcome, evidence
