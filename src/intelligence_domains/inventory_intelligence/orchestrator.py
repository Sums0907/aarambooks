import json
import uuid
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field

from src.brain_core.orchestration.orchestrator import BrainOrchestrator
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceRequirement
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement, SemanticConstraint
from src.intelligence_domains.inventory_intelligence.knowledge import InventorySemanticKnowledge

class DomainCaseState(str, Enum):
    INTENT_PARSING = "INTENT_PARSING"
    EVIDENCE_GATHERING = "EVIDENCE_GATHERING"
    REASONING = "REASONING"
    ACTION_FORMULATION = "ACTION_FORMULATION"
    RESOLUTION = "RESOLUTION"

class DomainCase(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    query: str
    state: DomainCaseState = DomainCaseState.INTENT_PARSING
    evidence_package: Optional[EvidencePackage] = None
    final_answer: Optional[str] = None

from src.brain_core.memory.interfaces import MemoryProvider, MemoryEntry

class InventoryIntelligenceOrchestrator:
    """
    IID-2: INVENTORY INTELLIGENCE SEMANTIC REQUIREMENT ENGINE.
    """
    def __init__(self, brain_orchestrator: BrainOrchestrator, gateway: ModelGatewayProvider, knowledge: InventorySemanticKnowledge, memory: Optional[MemoryProvider] = None):
        self._brain = brain_orchestrator
        self._gateway = gateway
        self._knowledge = knowledge
        self._memory = memory

    async def handle_query(self, query: str, user_id: str) -> str:
        case = DomainCase(user_id=user_id, query=query)

        # 1. INTENT PARSING (Semantic Requirement Engine)
        case.state = DomainCaseState.INTENT_PARSING
        
        capabilities = self._knowledge.get_certified_capabilities()
        unsupported = self._knowledge.get_unsupported_policies()
        
        cap_text = "\n".join([f"- Capability URN: {(c.metadata or {}).get('urn')} | Name: {c.concept_name} | Required: {(c.metadata or {}).get('required_constraints')} | Optional: {(c.metadata or {}).get('optional_constraints')} | Aliases: {c.aliases}" for c in capabilities])
        unsup_text = "\n".join([f"- {c.concept_name}: {c.description} (Aliases: {c.aliases})" for c in unsupported])
        
        system_prompt = f"""
You are the Inventory Intelligence Intent Parser.
Your job is to classify the user's natural language query into exactly one of the certified capabilities.

Certified Capabilities and their constraints:
{cap_text}

For business decisions like low stock, reorder points, valuation, aging, or severity, we do NOT have hardcoded policies.
- If the user asks for a decision but DOES NOT provide a specific threshold/rule (e.g. "Which are low stock?"), respond with:
{{
    "status": "CLARIFICATION_REQUIRED",
    "reason": "Ask the user what quantity or rule to use for 'low stock'."
}}
- If the user asks for a decision and DOES provide a rule (e.g. "Low stock means < 50"), extract the capability and include a decision_criteria field.

Respond with JSON:
{{
    "status": "SUPPORTED" or "CLARIFICATION_REQUIRED",
    "reason": "Optional clarification question",
    "requirement": {{
        "semantic_description": "Natural language summary of intent",
        "capability_urn": "urn:...",
        "constraints": [
            {{
                "identity": "inventory.entity.sku",
                "operator": "EQUALS | GREATER_THAN | LESS_THAN | GREATER_THAN_OR_EQUAL | LESS_THAN_OR_EQUAL | BETWEEN | IN | NOT_IN | NOT_EQUALS",
                "bound_value": "extracted value if present"
            }}
        ],
        "decision_criteria": "User-supplied rule if any, else null"
    }}
}}
"""
        
        request = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=system_prompt),
                GatewayMessage(role="user", content=query)
            ],
            temperature=0.0
        )
        
        response = await self._gateway.generate(request)
        response_text = response.content
        
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            parsed = json.loads(json_str)
        except Exception:
            return "I could not understand the intent."
            
        if parsed.get("status") == "UNSUPPORTED":
            case.final_answer = f"Unsupported: {parsed.get('reason')}"
            case.state = DomainCaseState.RESOLUTION
            return case.final_answer

        if parsed.get("status") == "CLARIFICATION_REQUIRED":
            case.final_answer = f"Clarification needed: {parsed.get('reason')}"
            case.state = DomainCaseState.RESOLUTION
            return case.final_answer

        # --- AZM VALIDATION ---
        req_data = parsed.get("requirement", {})
        target_urn = req_data.get("capability_urn")
        
        # Validate capability
        matching_cap = next((c for c in capabilities if (c.metadata or {}).get("urn") == target_urn), None)
        if not matching_cap:
            return f"Clarification needed: Capability {target_urn} is not a certified Inventory capability."
            
        required_identities = (matching_cap.metadata or {}).get("required_constraints", [])
        extracted_constraints = req_data.get("constraints", [])
        
        # Validate required constraints
        extracted_identities = [c.get("identity") for c in extracted_constraints]
        missing_required = [req for req in required_identities if req not in extracted_identities]
        
        if missing_required:
            return f"Clarification needed: Missing required constraints for this query: {', '.join(missing_required)}."
            
        # Construct explicit Generic Contracts
        req_id = str(uuid.uuid4())
        evidence_req = EvidenceRequirement(
            requirement_id=req_id,
            semantic_description=req_data.get("semantic_description", query),
            necessity="REQUIRED",
            rationale="User request"
        )
        
        resolved_req = ResolvedSemanticRequirement(
            requirement_id=req_id,
            original_requirement=evidence_req,
            semantic_constraints=[],
            semantic_gaps=[]
        )
        
        # Always add the capability itself as a constraint so Brain Core knows WHAT we want
        resolved_req.semantic_constraints.append(
            SemanticConstraint(
                identity=matching_cap.concept_id,
                constraint_type=matching_cap.concept_type,
                operator="EQUALS",
                bound_value=None
            )
        )
        
        ALLOWED_OPERATORS = {"EQUALS", "NOT_EQUALS", "GREATER_THAN", "GREATER_THAN_OR_EQUAL", "LESS_THAN", "LESS_THAN_OR_EQUAL", "IN", "NOT_IN", "BETWEEN"}

        for c in extracted_constraints:
            identity = c.get("identity")
            operator = c.get("operator", "EQUALS")
            
            if operator not in ALLOWED_OPERATORS:
                case.final_answer = f"Unsupported: Operator '{operator}' is not supported."
                case.state = DomainCaseState.RESOLUTION
                return case.final_answer

            # In a full implementation, we'd validate the identity against Azm entities
            resolved_req.semantic_constraints.append(
                SemanticConstraint(
                    identity=identity,
                    constraint_type="ENTITY" if "entity" in identity else "TEMPORAL", # Simplification for IID-2
                    operator=operator,
                    bound_value=c.get("bound_value")
                )
            )

        # 2. EVIDENCE GATHERING
        case.state = DomainCaseState.EVIDENCE_GATHERING
        
        # Call the new PUBLIC execution boundary, passing the fully resolved structured requirement!
        evidence_package = await self._brain.execute_requirements([resolved_req], case.user_id)
        case.evidence_package = evidence_package
        
        # 3. REASONING / GAP EVALUATION
        if evidence_package.sufficiency_assessment == "INSUFFICIENT":
            missing_caps = [g.value for g in evidence_package.gaps]
            case.final_answer = f"I cannot fully answer this question because required business data is unavailable. Gaps identified: {', '.join(missing_caps)}."
            case.state = DomainCaseState.RESOLUTION
            return case.final_answer
            
        case.state = DomainCaseState.REASONING

        evidence_text = ""
        if not evidence_package.evidence_items:
            evidence_text = "No relevant evidence was retrieved."
        else:
            for item in evidence_package.evidence_items:
                conf = getattr(item, "confidence_quality", "N/A")
                evidence_text += f"- [Source: {item.provenance.source_system} | Confidence: {conf}] {item.semantic_identity}: {json.dumps(item.data_payload)}\\n"

        certified_policies = self._knowledge.get_certified_policies()
        policy_text = "\\n".join([f"- {p.concept_name}: {p.description}" for p in certified_policies])

        partial_note = ""
        if evidence_package.sufficiency_assessment == "PARTIAL":
            partial_note = "NOTE: The evidence is PARTIAL. Some required data may be missing or failed to retrieve. Acknowledge this limitation to the user.\\n"

        decision_criteria = req_data.get("decision_criteria") if 'req_data' in locals() else None
        decision_note = ""
        if decision_criteria:
            decision_note = f"USER-SUPPLIED DECISION CRITERION: {decision_criteria}\\nYou must apply this rule when answering.\\n\\n"

        reasoning_prompt = (
            "You are the Aaram Inventory Intelligence Domain.\\n"
            "Your job is to answer the user's inventory question strictly using the provided Evidence.\\n"
            "DO NOT invent or estimate stock balances, prices, or movements.\\n"
            "If the evidence does not contain the answer, say so clearly.\\n"
            "You MUST apply the following certified Inventory policies when interpreting the evidence:\\n"
            f"{policy_text}\\n\\n"
            f"{partial_note}"
            f"{decision_note}"
            "Synthesize the facts into a clear, business-friendly response. If a decision rule was applied, state it."
        )
        
        user_prompt = f"User Query: {case.query}\\n\\nEvidence:\\n{evidence_text}"

        reason_req = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=reasoning_prompt),
                GatewayMessage(role="user", content=user_prompt)
            ],
            temperature=0.0
        )
        
        reason_res = await self._gateway.generate(reason_req)
        reasoning_content = reason_res.content.strip()

        case.state = DomainCaseState.ACTION_FORMULATION

        action_prompt = (
            "Based on the following user query and reasoning, determine if an ACTION or ESCALATION is required.\\n"
            "If the user asks for someone to review, intervene, or if an exception is severe, formulate a HUMAN_ASSISTANCE action.\\n"
            "If no action is explicitly required or implied, output 'NO_ACTION'.\\n"
            "Otherwise, output JSON:\\n"
            "{\\n"
            '    "category": "human_assistance",\\n'
            '    "reasoning": "Why this action is needed",\\n'
            '    "parameters": {"context": "..."}\\n'
            "}\\n"
        )
        
        action_req = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=action_prompt),
                GatewayMessage(role="user", content=f"Query: {case.query}\\nReasoning: {reasoning_content}")
            ],
            temperature=0.0
        )
        
        action_res = await self._gateway.generate(action_req)
        action_content = action_res.content.strip()

        final_answer = reasoning_content

        if "NO_ACTION" not in action_content:
            try:
                from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory
                from src.event_bus.dispatcher import OutboundDispatcher
                
                if "```json" in action_content:
                    json_str = action_content.split("```json")[1].split("```")[0].strip()
                else:
                    json_str = action_content.strip()
                
                parsed_action = json.loads(json_str)
                action_req_obj = ActionRequest(
                    category=ActionCategory(parsed_action["category"]),
                    reasoning=parsed_action["reasoning"],
                    parameters=parsed_action.get("parameters", {})
                )
                
                dispatched_action = OutboundDispatcher.dispatch(action_req_obj)
                final_answer += f"\\n\\n[Action Dispatched]: {dispatched_action}"
            except Exception:
                pass

        case.final_answer = final_answer
        case.state = DomainCaseState.RESOLUTION
        
        if self._memory:
            provenance = "USER_SUPPLIED" if decision_criteria else "DOMAIN_POLICY"
            entry = MemoryEntry(
                content=case.final_answer,
                metadata={
                    "case_id": case.case_id,
                    "query": case.query,
                    "decision_criteria": decision_criteria,
                    "criteria_provenance": provenance
                }
            )
            await self._memory.write_memory(entry, session_id=user_id)
        
        return case.final_answer
