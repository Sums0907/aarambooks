import json
from typing import Optional, Tuple
from src.shared.cognitive_planning_contracts import EvidencePackage
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
from src.brain_core.knowledge.interfaces import KnowledgeProvider, KnowledgeQuery
from src.brain_core.memory.interfaces import MemoryProvider, MemoryQuery, MemoryEntry
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory
from src.brain_core.decision.interfaces import DecisionRecommendation, DecisionAlternative

class NDRIntelligenceOrchestrator:
    def __init__(self, gateway: ModelGatewayProvider, knowledge: KnowledgeProvider, memory: MemoryProvider):
        self.gateway = gateway
        self.knowledge = knowledge
        self.memory = memory

    async def orchestrate_resolution(
        self, 
        trigger_evidence: EvidencePackage
    ) -> Tuple[DecisionRecommendation, Optional[ActionRequest], Optional[str]]:
        
        # 0. Extract trigger facts from inbound evidence
        item = trigger_evidence.evidence_items[0] if trigger_evidence.evidence_items else None
        payload = item.data_payload if item else {}
        
        shipment_data = payload.get("shipment_context", {})
        shipment_id = shipment_data.get("shipment_id", "unknown")
        
        customer_data = payload.get("customer_context", {})
        order_data = payload.get("order_context")

        # 1. Fetch relevant knowledge
        policies = await self.knowledge.search_knowledge(
            KnowledgeQuery(query_text="NDR resolution rules policies", domain="ndr", limit=2)
        )
        policy_text = "\n".join([p.content for p in policies]) if policies else "Default Policy: Attempt redelivery up to 3 times."

        # 2. Fetch past memory/NDR history for this shipment
        session_id = f"ndr_shipment_{shipment_id}"
        past_memories = await self.memory.read_memory(MemoryQuery(session_id=session_id))
        history_text = "No prior NDR history."
        if past_memories:
            history_text = "\n".join([f"- {m.content}" for m in past_memories])

        # 3. Formulate LLM reasoning request
        system_prompt = (
            "You are the NDR Intelligence Reasoning Engine.\n"
            f"Knowledge/Policies:\n{policy_text}\n\n"
            f"Past Resolution History for this Shipment:\n{history_text}\n\n"
            "Analyze the NDR and recommend a resolution. Output strictly as JSON containing:\n"
            "{\n"
            '  "intent": "string",\n'
            '  "customer_message": "string (optional message to customer)",\n'
            '  "escalation_needed": bool,\n'
            '  "action_category": "string (one of: recommendation, suggested_resolution, automated_response, human_assistance)",\n'
            '  "justification": "string"\n'
            "}"
        )
        
        user_prompt = f"Shipment: {json.dumps(shipment_data)}\nCustomer: {json.dumps(customer_data)}"

        request = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=system_prompt),
                GatewayMessage(role="user", content=user_prompt)
            ],
            temperature=0.0 # Deterministic reasoning
        )
        
        # 4. Execute via Gateway
        response = await self.gateway.generate(request)
        
        # 5. Parse reasoning output safely
        content = response.content
        if content.startswith("```json"):
            content = content[7:-3]
            
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Handle ambiguous/invalid output safely
            decision = DecisionRecommendation(
                recommended_alternative_id="escalate",
                alternatives_considered=[],
                justification="Failed to parse LLM response securely."
            )
            action = ActionRequest(
                category=ActionCategory.HUMAN_ASSISTANCE,
                reasoning="Safety escalation due to parse failure.",
                parameters={"shipment_id": shipment_id}
            )
            # Persist resolution attempt to Memory
            await self.memory.write_memory(
                MemoryEntry(
                    content=f"NDR Resolution Evaluated: {decision.recommended_alternative_id} - {decision.justification}",
                    metadata={"shipment_id": shipment_id, "escalated": True}
                ),
                session_id=session_id
            )
            return decision, action, None

        # 6. Formulate strict governed objects
        is_escalation = parsed.get("escalation_needed", False)
        
        # Convert category string to Enum safely
        cat_str = parsed.get("action_category", "suggested_resolution")
        try:
            category = ActionCategory(cat_str)
        except ValueError:
            category = ActionCategory.SUGGESTED_RESOLUTION
            
        if is_escalation:
            category = ActionCategory.HUMAN_ASSISTANCE

        decision = DecisionRecommendation(
            recommended_alternative_id=parsed.get("intent", "unknown"),
            alternatives_considered=[
                DecisionAlternative(
                    id=parsed.get("intent", "unknown"),
                    description="Recommended resolution path",
                    confidence=0.9 if not is_escalation else 0.4,
                    reasoning=parsed.get("justification", ""),
                    expected_outcomes=["resolution"]
                )
            ],
            justification=parsed.get("justification", "")
        )

        action = ActionRequest(
            category=category,
            reasoning=decision.justification,
            parameters={"shipment_id": shipment_id, "intent": parsed.get("intent")}
        )

        customer_message = parsed.get("customer_message")
        
        # 7. Persist resolution attempt to Memory
        await self.memory.write_memory(
            MemoryEntry(
                content=f"NDR Resolution Evaluated: {decision.recommended_alternative_id} - {decision.justification}",
                metadata={"shipment_id": shipment_id, "escalated": is_escalation}
            ),
            session_id=session_id
        )

        return decision, action, customer_message
