import json
from typing import Optional, Tuple
from src.brain_core.models.contexts import CustomerContext, OrderContext
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
from src.brain_core.knowledge.interfaces import KnowledgeProvider, KnowledgeQuery
from src.brain_core.memory.interfaces import MemoryProvider, MemoryQuery, MemoryEntry
from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory
from src.brain_core.decision.interfaces import DecisionRecommendation, DecisionAlternative

class CustomerQueryOrchestrator:
    def __init__(self, gateway: ModelGatewayProvider, knowledge: KnowledgeProvider, memory: MemoryProvider):
        self.gateway = gateway
        self.knowledge = knowledge
        self.memory = memory

    async def handle_query(
        self, 
        query_text: str,
        customer_context: CustomerContext,
        order_context: Optional[OrderContext] = None,
        session_id: Optional[str] = None
    ) -> Tuple[str, DecisionRecommendation, Optional[ActionRequest]]:
        
        # 1. Fetch relevant knowledge
        policies = await self.knowledge.search_knowledge(
            KnowledgeQuery(query_text=query_text, domain="customer_support", limit=2)
        )
        policy_text = "\n".join([p.content for p in policies]) if policies else "No specific policy."

        # 2. Fetch past memory/conversation state
        conversation_history_text = "No prior conversation history."
        if session_id:
            past_memories = await self.memory.read_memory(MemoryQuery(session_id=session_id))
            if past_memories:
                conversation_history_text = "\n".join([f"- {m.content}" for m in past_memories])

        # 3. Formulate LLM reasoning request
        system_prompt = (
            "You are the Customer Query Intelligence Engine.\n"
            f"Knowledge/Policies:\n{policy_text}\n\n"
            f"Conversation History:\n{conversation_history_text}\n\n"
            "Analyze the customer's message and context. Output strictly as JSON containing:\n"
            "{\n"
            '  "intent": "string",\n'
            '  "response_text": "string (the exact reply to the customer)",\n'
            '  "escalation_needed": bool,\n'
            '  "requires_action": bool,\n'
            '  "justification": "string"\n'
            "}"
        )
        
        customer_data = customer_context.model_dump_json()
        order_data = order_context.model_dump_json() if order_context else "None"
        
        user_prompt = f"Customer Query: {query_text}\nCustomer Context: {customer_data}\nOrder Context: {order_data}"

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
                parameters={"customer_id": customer_context.customer_id}
            )
            response_text = "I apologize, but I am having trouble processing your request. I will escalate this to a human agent."
            # Persist interaction to Memory
            if session_id:
                await self.memory.write_memory(
                    MemoryEntry(
                        content=f"User: {query_text}\nAssistant: {response_text}",
                        metadata={"intent": decision.recommended_alternative_id, "escalated": True}
                    ),
                    session_id=session_id
                )
            return response_text, decision, action

        # 6. Formulate strict governed objects
        is_escalation = parsed.get("escalation_needed", False)
        requires_action = parsed.get("requires_action", False)
        response_text = parsed.get("response_text", "An agent will contact you shortly.")
        
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

        action = None
        if requires_action or is_escalation:
            category = ActionCategory.HUMAN_ASSISTANCE if is_escalation else ActionCategory.SUGGESTED_RESOLUTION
            action = ActionRequest(
                category=category,
                reasoning=decision.justification,
                parameters={"customer_id": customer_context.customer_id, "intent": parsed.get("intent")}
            )

        # 7. Persist interaction to Memory
        if session_id:
            await self.memory.write_memory(
                MemoryEntry(
                    content=f"User: {query_text}\nAssistant: {response_text}",
                    metadata={"intent": decision.recommended_alternative_id, "escalated": is_escalation}
                ),
                session_id=session_id
            )

        return response_text, decision, action
