import json
import uuid
import re
import logging
from datetime import datetime, UTC
from typing import Optional, Tuple, List, Dict, Any

from src.shared.cognitive_planning_contracts import (
    EvidencePackage,
    EvidenceItem,
    ProvenanceMetadata
)
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
    ExecutionLimitation
)
from src.shared.requirement_classification_contracts import ClassifiedRequirement
from src.shared.memory_contracts import ConversationTurn
from src.shared.conversational_contracts import (
    ConversationalUnderstanding,
    ConversationalIntent,
    SemanticEntityReference,
    InformationSource,
    ConversationalResponse,
    ConversationalResponseType
)
from src.brain_core.gateway.interfaces import (
    ModelGatewayProvider,
    GatewayGenerationRequest,
    GatewayMessage
)
from src.brain_core.knowledge.interfaces import KnowledgeProvider, KnowledgeQuery
from src.brain_core.memory.interfaces import MemoryProvider, MemoryQuery, MemoryEntry
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory
from src.brain_core.decision.interfaces import DecisionRecommendation, DecisionAlternative

from src.intelligence_domains.ndr.models import (
    NDRCase,
    NDRContext,
    FailureDiagnosis,
    CustomerState,
    PriorityAndRiskEvaluation,
    RecoveryStrategy,
    InterventionRecommendation,
    DownstreamOutcomeSignal,
    OutcomeEvaluation,
    LearningEvidence,
    CaseLifecycleState
)
from src.intelligence_domains.ndr.knowledge import (
    NDRDiagnosticEngine,
    NDRPriorityRiskEngine,
    NDRStrategyEngine,
    NDROutcomeEvaluator
)

logger = logging.getLogger(__name__)

# ── Statuses that indicate the NDR is already closed — no action needed ───────
_CLOSED_NDR_STATUSES = {
    "delivered", "rto_initiated", "rto_delivered", "cancelled",
    "returned", "closed", "resolved", "lost", "expired"
}

class NDRIntelligenceOrchestrator:
    """
    NDR Resolution Intelligence Domain Orchestrator.
    Implements IntelligenceDomainProvider protocol for Rabta conversational queries
    and provides event-driven resolution orchestration.
    """
    def __init__(
        self,
        gateway: ModelGatewayProvider,
        knowledge: KnowledgeProvider,
        memory: MemoryProvider,
        azm_provider: Any = None
    ):
        self.gateway = gateway
        self.knowledge = knowledge
        self.memory = memory
        self.azm_provider = azm_provider

    # =========================================================================
    # 1. Rabta R-1: Conversational Understanding & Entity Extraction
    # =========================================================================
    async def extract_understanding(
        self,
        query: Any,
        history: Optional[List[ConversationTurn]] = None
    ) -> ConversationalUnderstanding:
        from src.shared.conversational_contracts import MultimodalQuery, SemanticAttribute, InformationSource
        
        if isinstance(query, MultimodalQuery):
            query_text = query.text
            context_metadata = query.context_metadata or {}
        else:
            query_text = str(query)
            context_metadata = {}

        query_lower = query_text.lower()
        entities: List[SemanticEntityReference] = []
        attributes: List[SemanticAttribute] = []

        # Extract AWB number (e.g. AWB12345, 14371289123, etc.)
        awb_match = re.search(r'\b(?:awb\s*[:#-]?\s*|\b)([A-Z0-9]{8,16})\b', query_text, re.IGNORECASE)
        if awb_match:
            entities.append(SemanticEntityReference(
                original_expression=awb_match.group(1),
                source=InformationSource.EXPLICIT,
                inferred_type="ndr.entity.awb"
            ))
            
        # Extract preferred_date via Gateway if context is present
        session_timestamp = context_metadata.get("session_timestamp")
        if session_timestamp and self.gateway:
            system_prompt = (
                "You are an assistant. Extract any customer-requested delivery reattempt date from the conversation transcript. "
                f"Resolve relative dates (like 'tomorrow') against this System Context Timestamp: {session_timestamp}. "
                "Return ONLY a JSON object: {\"preferred_date\": \"YYYY-MM-DD\"} or {\"preferred_date\": null}."
            )
            try:
                req = GatewayGenerationRequest(
                    messages=[
                        GatewayMessage(role="system", content=system_prompt),
                        GatewayMessage(role="user", content=query_text)
                    ],
                    model="local-qwen"
                )
                resp = await self.gateway.generate(req)
                content = resp.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                parsed = json.loads(content)
                pref_date = parsed.get("preferred_date")
                if pref_date:
                    attributes.append(SemanticAttribute(
                        attribute_name="customer.attribute.preferred_date",
                        original_expression=pref_date,
                        source=InformationSource.INFERRED
                    ))
            except Exception as e:
                logger.error(f"Date extraction failed: {e}")

        # Classify intent
        if any(w in query_lower for w in ["reschedule", "retry", "reattempt", "change date", "dispute", "update address"]):
            intent = ConversationalIntent.ACTION
        elif any(w in query_lower for w in ["why", "reason", "diagnose", "explain", "how come"]):
            intent = ConversationalIntent.EXPLAIN
        else:
            intent = ConversationalIntent.RETRIEVE

        return ConversationalUnderstanding(
            original_query=query_text,
            intent=intent,
            entities=entities,
            attributes=attributes
        )

    # =========================================================================
    # 3. Rabta R-8: Conversational Interpretation & Response Generation
    # =========================================================================
    async def interpret_evidence(self, response: Any) -> ConversationalResponse:
        if isinstance(response, BusinessEvidenceResponse):
            if response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE:
                msg = "NDR shipment record located. Delivery exception details and recovery options are ready."
            elif response.status == BusinessRealityStatus.ENTITY_NOT_FOUND:
                msg = "No delivery exception records found matching the requested tracking reference."
            else:
                msg = f"NDR record retrieved with status: {response.status.value}"
        elif isinstance(response, DecisionRecommendation):
            msg = f"Recommendation: {response.justification}"
        else:
            msg = str(response)

        return ConversationalResponse(
            response_type=ConversationalResponseType.SUCCESS,
            message=msg
        )

    # =========================================================================
    # 4. Event-Driven Full Resolution Lifecycle
    # =========================================================================
    async def orchestrate_resolution(
        self,
        trigger_evidence: EvidencePackage
    ) -> Tuple[DecisionRecommendation, Optional[ActionRequest], Optional[str]]:

        # ── Step 0 & 1: Extract Semantic NDR Context Across All Evidence ───────
        # Aggregate semantic evidence across all items sequentially.
        payload = {}
        for item in trigger_evidence.evidence_items:
            # Overwrite earlier evidence with later evidence (assuming chronological order)
            if item.data_payload:
                payload.update(item.data_payload)
        
        # Determine Canonical Shipment Identity
        awb_no = payload.get("ndr.entity.awb") or "UNKNOWN_AWB"

        if awb_no == "UNKNOWN_AWB":
            logger.warning("NDR event received with no canonical AWB identity. Skipping.")
            return self._noop_decision("No AWB provided"), None, None
            
        ndr_status = (payload.get("ndr.vocabulary.ndr_status") or payload.get("shopdeck.metric.ndr_status") or "unknown").lower().strip()
        order_status = (payload.get("shopdeck.metric.order_status") or "unknown").lower().strip()

        if ndr_status in _CLOSED_NDR_STATUSES or order_status in _CLOSED_NDR_STATUSES:
            logger.info(f"[NDR-ID] AWB {awb_no}: Skipping — NDR is already closed (ndr_status={ndr_status}, order_status={order_status})")
            return self._noop_decision(f"NDR already closed: {ndr_status or order_status}"), None, None

        courier_partner = payload.get("ndr.entity.courier_partner", "Unknown")
        attempt_count = int(payload.get("shopdeck.metric.ndr_count") or 1)
        latest_reason = payload.get("shopdeck.event.delivery_exception.reason") or "Customer unavailable"
        payment_mode = payload.get("shopdeck.entity.payment.mode", "cod")
        customer_name = payload.get("ndr.entity.customer")
        customer_id = payload.get("ndr.entity.customer_id") # Note: assuming customer id if mapped
        order_value = float(payload.get("shopdeck.entity.order.gross_value") or 0.0)

        context = NDRContext(
            awb_no=awb_no,
            courier_partner=courier_partner,
            order_id=payload.get("ndr.entity.order_id"),
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=payload.get("customer.attribute.phone"), # Keeping derived intent/sentiment as they are
            payment_mode=payment_mode,
            order_value=order_value,
            attempt_count=attempt_count,
            latest_ndr_reason=latest_reason
        )

        logger.info(
            f"[NDR-ID] AWB {awb_no}: ACTIVE NDR — reason='{latest_reason}', "
            f"attempts={attempt_count}, payment={payment_mode}, courier={courier_partner}"
        )

        # ── Step 4: Failure Diagnosis ─────────────────────────────────────────
        diagnosis = NDRDiagnosticEngine.diagnose_failure(latest_reason, courier_partner, attempt_count)
        logger.info(f"[NDR-ID] AWB {awb_no}: Diagnosed as {diagnosis.category.value} (confidence={diagnosis.confidence})")

        # ── Step 5: Parse customer state / sentiment if available ─────────────
        customer_state = CustomerState(
            intent=payload.get("customer.state.intent", "PENDING_CONTACT"),
            sentiment=payload.get("customer.state.sentiment", "NEUTRAL"),
            preferred_reattempt_date=payload.get("customer.attribute.preferred_date")
        )

        # ── Step 6: Priority & Risk Evaluation ───────────────────────────────
        risk = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diagnosis, customer_state)

        # ── Step 7: Recovery Strategy Determination ───────────────────────────
        strategy, recommendation = NDRStrategyEngine.determine_strategy(context, diagnosis, risk, customer_state)
        logger.info(f"[NDR-ID] AWB {awb_no}: Strategy={strategy.strategy_name} | Action={recommendation.action_type}")

        # ── Step 8: Formulate Governed Decision Recommendation ────────────────
        decision = DecisionRecommendation(
            recommended_alternative_id=strategy.strategy_type.value,
            alternatives_considered=[
                DecisionAlternative(
                    id=strategy.strategy_type.value,
                    description=strategy.strategy_name,
                    confidence=strategy.confidence,
                    reasoning=strategy.rationale,
                    expected_outcomes=["delivery_recovery", "rto_avoidance"]
                )
            ],
            justification=(
                f"[{strategy.strategy_name}] {strategy.rationale} "
                f"(Operational Risk: {risk.operational_risk_score}, "
                f"Commercial Priority: {risk.commercial_priority_score})"
            )
        )

        # ── Step 9: Formulate Governed Action Request ─────────────────────────
        from src.brain_core.action_engine.contracts import ConversationalDirective
        
        directive = ConversationalDirective(
            objective=strategy.target_objective,
            context_summary=strategy.rationale,
            allowed_actions=[recommendation.action_type],
            constraints=["Do not explicitly name the courier partner in conversation", "Acknowledge the customer's intent clearly"]
        )

        action = ActionRequest(
            action_request_id=f"act_{uuid.uuid4().hex[:8]}",
            category=recommendation.action_category,
            reasoning=recommendation.justification,
            parameters=recommendation.parameters,
            execution_intent=recommendation.execution_intent,
            directive=directive
        )

        # ── Step 10: Persist Case Evidence to Domain Memory ──────────────────
        session_id = f"ndr_shipment_{awb_no}"
        await self.memory.write_memory(
            MemoryEntry(
                content=(
                    f"NDR Triage Formulated: Strategy={strategy.strategy_type.value}, "
                    f"Action={recommendation.action_type}, Risk={risk.operational_risk_score}, "
                    f"Priority={risk.commercial_priority_score}"
                ),
                metadata={
                    "awb_no": awb_no,
                    "strategy": strategy.strategy_type.value,
                    "action_category": recommendation.action_category.value,
                    "operational_risk": risk.operational_risk_score,
                    "commercial_priority": risk.commercial_priority_score,
                    "requires_human_approval": recommendation.requires_human_approval
                }
            ),
            session_id=session_id
        )

        return decision, action, recommendation.customer_message

    def _noop_decision(self, reason: str) -> DecisionRecommendation:
        """Returns a no-op decision for closed/ineligible NDRs."""
        return DecisionRecommendation(
            recommended_alternative_id="NO_ACTION",
            alternatives_considered=[],
            justification=reason
        )

    # =========================================================================
    # 5. Outcome Evaluation & Learning Evidence Loop
    # =========================================================================
    async def evaluate_and_record_outcome(
        self,
        case_id: str,
        awb_no: str,
        strategy: RecoveryStrategy,
        signal: DownstreamOutcomeSignal,
        order_value: float = 0.0
    ) -> Tuple[OutcomeEvaluation, LearningEvidence]:
        outcome, evidence = NDROutcomeEvaluator.evaluate_outcome(
            case_id=case_id,
            awb_no=awb_no,
            strategy=strategy,
            signal=signal,
            order_value=order_value
        )

        # Persist structured outcome evidence to memory
        session_id = f"ndr_learning_{awb_no}"
        await self.memory.write_memory(
            MemoryEntry(
                content=evidence.evidence_text,
                metadata={
                    "case_id": case_id,
                    "awb_no": awb_no,
                    "strategy": strategy.strategy_type.value,
                    "recovered": outcome.was_delivery_recovered,
                    "rto_avoided": outcome.was_rto_avoided,
                    "revenue_protected": outcome.revenue_protected
                }
            ),
            session_id=session_id
        )

        return outcome, evidence
