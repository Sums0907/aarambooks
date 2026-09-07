from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from src.brain_core.action_engine.contracts import ActionCategory

class FailureCategory(str, Enum):
    CUSTOMER_UNAVAILABLE = "CUSTOMER_UNAVAILABLE"
    BUYER_REMORSE_OR_REJECTION = "BUYER_REMORSE_OR_REJECTION"
    SUSPECTED_FAKE_ATTEMPT = "SUSPECTED_FAKE_ATTEMPT"
    ADDRESS_OR_LOCATION_DEFECT = "ADDRESS_OR_LOCATION_DEFECT"
    OPERATIONAL_OR_TRANSIT_DELAY = "OPERATIONAL_OR_TRANSIT_DELAY"
    UNKNOWN = "UNKNOWN"

class StrategyPatternType(str, Enum):
    AUTONOMOUS_RESCHEDULE = "AUTONOMOUS_RESCHEDULE"
    DOORSTEP_VERIFICATION_AND_DISPUTE = "DOORSTEP_VERIFICATION_AND_DISPUTE"
    BUYER_INTENT_CONFIRMATION = "BUYER_INTENT_CONFIRMATION"
    ADDRESS_AND_LANDMARK_ENRICHMENT = "ADDRESS_AND_LANDMARK_ENRICHMENT"
    PRIORITY_CONCIERGE_ESCALATION = "PRIORITY_CONCIERGE_ESCALATION"
    BUYER_COMMITMENT_AND_PREPAYMENT = "BUYER_COMMITMENT_AND_PREPAYMENT"
    NO_ACTION = "NO_ACTION"

class CaseLifecycleState(str, Enum):
    CASE_CREATED = "CASE_CREATED"
    CONTEXT_ASSEMBLED = "CONTEXT_ASSEMBLED"
    FAILURE_DIAGNOSED = "FAILURE_DIAGNOSED"
    STRATEGY_FORMULATED = "STRATEGY_FORMULATED"
    INTERACTION_ACTIVE = "INTERACTION_ACTIVE"
    RECOMMENDATION_READY = "RECOMMENDATION_READY"
    EXECUTION_PENDING = "EXECUTION_PENDING"
    EXECUTION_ACKNOWLEDGED = "EXECUTION_ACKNOWLEDGED"
    OUTCOME_OBSERVED = "OUTCOME_OBSERVED"
    OUTCOME_EVALUATED = "OUTCOME_EVALUATED"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    CASE_CLOSED = "CASE_CLOSED"

class NDREvent(BaseModel):
    awb_no: str
    courier_partner: str
    failure_code: str
    failure_description: str
    attempt_count: Optional[int] = None
    order_id: Optional[str] = None
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class NDRContext(BaseModel):
    awb_no: str
    courier_partner: str
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_mode: Optional[str] = None
    order_value: Optional[float] = None
    attempt_count: Optional[int] = None
    ofd_count: Optional[int] = None
    latest_ndr_reason: Optional[str] = None
    destination_city: Optional[str] = None
    destination_pincode: Optional[str] = None
    item_summary: Optional[str] = None
    prior_actions: List[Dict[str, Any]] = Field(default_factory=list)

class FailureDiagnosis(BaseModel):
    category: FailureCategory
    root_cause_explanation: str
    is_carrier_disputed: bool = False
    confidence: float = 1.0

class CustomerState(BaseModel):
    intent: str = "PENDING_CONTACT"
    sentiment: str = "NEUTRAL"
    preferred_reattempt_date: Optional[str] = None
    landmark_enrichment: Optional[str] = None
    verified_doorstep_attempt: Optional[bool] = None

class PriorityAndRiskEvaluation(BaseModel):
    operational_risk_score: float = Field(..., ge=0.0, le=1.0, description="Probability of delivery failure based on attempts and logistics factors")
    commercial_priority_score: float = Field(..., ge=0.0, le=1.0, description="Commercial value and margin importance")
    customer_experience_risk_score: float = Field(..., ge=0.0, le=1.0, description="Customer relationship and churn impact")
    rto_probability: float = Field(..., ge=0.0, le=1.0)
    recovery_probability: float = Field(..., ge=0.0, le=1.0)
    policy_allows_autonomous_action: bool = True
    policy_constraint_notes: Optional[str] = None

class RecoveryStrategy(BaseModel):
    strategy_type: StrategyPatternType
    strategy_name: str
    target_objective: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str

class InterventionRecommendation(BaseModel):
    recommendation_id: str
    action_type: str
    action_category: ActionCategory
    parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_intent: Optional[Any] = None
    justification: str
    customer_message: Optional[str] = None
    requires_human_approval: bool = False

class DownstreamOutcomeSignal(BaseModel):
    awb_no: str
    order_status: str
    delivery_time: Optional[datetime] = None
    execution_confirmed: Optional[bool] = None
    customer_engaged: Optional[bool] = None
    delivery_recovered: Optional[bool] = None
    rto_avoided: Optional[bool] = None
    is_final_rto: Optional[bool] = None

class OutcomeEvaluation(BaseModel):
    case_id: str
    awb_no: str
    strategy_attempted: StrategyPatternType
    was_recommendation_accepted: Optional[bool] = None
    was_action_executed: Optional[bool] = None
    was_customer_engaged: Optional[bool] = None
    was_delivery_recovered: Optional[bool] = None
    was_rto_avoided: Optional[bool] = None
    revenue_protected: Optional[float] = None
    freight_saved: Optional[float] = None
    evaluation_summary: str = ""

class LearningEvidence(BaseModel):
    case_id: str
    awb_no: str
    courier_partner: Optional[str] = None
    failure_category: Optional[FailureCategory] = None
    strategy_used: StrategyPatternType
    recovered: Optional[bool] = None
    evidence_text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class NDRCase(BaseModel):
    case_id: str
    awb_no: str
    current_state: CaseLifecycleState = CaseLifecycleState.CASE_CREATED
    context: Optional[NDRContext] = None
    diagnosis: Optional[FailureDiagnosis] = None
    customer_state: Optional[CustomerState] = None
    priority_and_risk: Optional[PriorityAndRiskEvaluation] = None
    active_strategy: Optional[RecoveryStrategy] = None
    recommendation: Optional[InterventionRecommendation] = None
    outcome: Optional[OutcomeEvaluation] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
