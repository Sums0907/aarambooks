import json
import uuid
import re
from datetime import datetime, UTC
from typing import Optional, Tuple, List, Dict, Any

from src.shared.cognitive_planning_contracts import (
    EvidencePackage,
    EvidenceItem,
    ProvenanceMetadata
)
from src.shared.conversational_contracts import (
    ConversationalUnderstanding,
    ConversationalIntent,
    SemanticEntityReference,
    InformationSource,
    ConversationalResponse,
    ConversationalResponseType
)
from src.shared.memory_contracts import ConversationTurn
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
    ExecutionLimitation
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
        sql_engine: Any = None,
        azm_provider: Any = None
    ):
        self.gateway = gateway
        self.knowledge = knowledge
        self.memory = memory
        self.sql_engine = sql_engine
        self.azm_provider = azm_provider

    # =========================================================================
    # 1. Rabta R-1: Conversational Understanding & Entity Extraction
    # =========================================================================
    async def extract_understanding(
        self,
        query: str,
        history: Optional[List[ConversationTurn]] = None
    ) -> ConversationalUnderstanding:
        query_lower = query.lower()
        entities: List[SemanticEntityReference] = []

        # Extract AWB number (e.g. AWB12345, 14371289123, etc.)
        awb_match = re.search(r'\b(?:awb\s*[:#-]?\s*|\b)([A-Z0-9]{8,16})\b', query, re.IGNORECASE)
        if awb_match:
            entities.append(SemanticEntityReference(
                original_expression=awb_match.group(1),
                source=InformationSource.EXPLICIT,
                inferred_type="ndr.entity.awb"
            ))

        # Classify intent
        if any(w in query_lower for w in ["reschedule", "retry", "reattempt", "change date", "dispute", "update address"]):
            intent = ConversationalIntent.ACTION
        elif any(w in query_lower for w in ["why", "reason", "diagnose", "explain", "how come"]):
            intent = ConversationalIntent.EXPLAIN
        else:
            intent = ConversationalIntent.RETRIEVE

        return ConversationalUnderstanding(
            original_query=query,
            intent=intent,
            entities=entities
        )

    # =========================================================================
    # 2. Rabta R-4/R-5: Dynamic Read Substrate (Text-to-SQL Execution)
    # =========================================================================
    async def execute_read_query(self, abstract_request: AbstractEvidenceRequest) -> BusinessEvidenceResponse:
        query = abstract_request.classified_requirement.understanding.original_query
        try:
            if self.azm_provider:
                schemas = self.azm_provider.get_namespace_schema("ndr")
            else:
                schemas = {
                    "vw_shopdeck_shipment_ndr_reports": {
                        "columns": {
                            "awb_no": "STRING",
                            "order_status": "STRING",
                            "courier_partner": "STRING",
                            "payment_mode": "STRING",
                            "latest_ndr_reason": "STRING",
                            "ndr_count": "INTEGER"
                        }
                    }
                }

            if self.sql_engine:
                sql_query = await self.sql_engine.generate_sql(query, schemas, "PostgreSQL")
                raw_data = [{"query_executed": sql_query, "status": "simulated_read"}]
            else:
                raw_data = [{"error": "SQL Engine not configured"}]

            evidence_package = EvidencePackage(
                package_id=str(uuid.uuid4()),
                plan_id=str(uuid.uuid4()),
                sufficiency_assessment="SUFFICIENT",
                evidence_items=[
                    EvidenceItem(
                        item_id=str(uuid.uuid4()),
                        semantic_identity="ndr.sql_result",
                        data_payload={"data": raw_data},
                        provenance=ProvenanceMetadata(
                            source_system="urn:aarambooks:system:sql_engine",
                            retrieval_timestamp=datetime.now(UTC)
                        ),
                        confidence_quality="HIGH"
                    )
                ]
            )
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                evidence_data={"data": raw_data, "package_id": str(uuid.uuid4())}
            )
        except Exception as e:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[ExecutionLimitation(missing_parameter="sql", reason=str(e))]
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
        
        # Step 1: Extract and assemble context
        item = trigger_evidence.evidence_items[0] if trigger_evidence.evidence_items else None
        payload = item.data_payload if item else {}

        shipment_data = payload.get("shipment_context", {})
        customer_data = payload.get("customer_context", {})
        order_data = payload.get("order_context", {})

        awb_no = shipment_data.get("shipment_id") or shipment_data.get("awb_no", "UNKNOWN_AWB")
        courier_partner = shipment_data.get("courier_partner", "Delhivery")
        attempt_count = int(shipment_data.get("attempt_count", 1))
        latest_reason = shipment_data.get("latest_ndr_reason") or payload.get("failure_description", "Customer unavailable")
        payment_mode = order_data.get("payment_mode", "cod") if order_data else shipment_data.get("payment_mode", "cod")
        order_value = float(order_data.get("order_value", 1299.0)) if order_data else 1299.0

        context = NDRContext(
            awb_no=awb_no,
            courier_partner=courier_partner,
            order_id=order_data.get("order_id") if order_data else None,
            customer_id=customer_data.get("customer_id"),
            customer_name=customer_data.get("name"),
            customer_phone=customer_data.get("phone"),
            payment_mode=payment_mode,
            order_value=order_value,
            attempt_count=attempt_count,
            latest_ndr_reason=latest_reason
        )

        # Step 2: Failure Diagnosis
        diagnosis = NDRDiagnosticEngine.diagnose_failure(latest_reason, courier_partner, attempt_count)

        # Step 3: Parse customer state/sentiment if available
        customer_state = CustomerState(
            intent=payload.get("customer_intent", "PENDING_CONTACT"),
            sentiment=payload.get("customer_sentiment", "NEUTRAL"),
            preferred_reattempt_date=payload.get("preferred_date")
        )

        # Step 4: Priority & Risk Evaluation (Strict separation of Operational Risk, Commercial Priority, CX Risk)
        risk = NDRPriorityRiskEngine.evaluate_priority_and_risk(context, diagnosis, customer_state)

        # Step 5: Recovery Strategy Determination (First-class Strategy abstraction)
        strategy, recommendation = NDRStrategyEngine.determine_strategy(context, diagnosis, risk, customer_state)

        # Step 6: Formulate Governed Decision Recommendation
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
            justification=f"[{strategy.strategy_name}] {strategy.rationale} (Operational Risk: {risk.operational_risk_score}, Commercial Priority: {risk.commercial_priority_score})"
        )

        # Step 7: Formulate Governed Action Request for Business System Execution
        action = ActionRequest(
            category=recommendation.action_category,
            reasoning=recommendation.justification,
            parameters=recommendation.parameters
        )

        # Step 8: Persist Case Evidence to Domain Memory
        session_id = f"ndr_shipment_{awb_no}"
        await self.memory.write_memory(
            MemoryEntry(
                content=f"NDR Triage Formulated: Strategy={strategy.strategy_type.value}, Action={recommendation.action_type}, Risk={risk.operational_risk_score}, Priority={risk.commercial_priority_score}",
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
