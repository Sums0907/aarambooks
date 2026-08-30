from typing import Dict, Any, Optional
import json
import uuid

from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
from src.shared.cognitive_planning_contracts import EvidencePlan, EvidenceRequirement, EvidencePlanExtension, EvidencePackage

class CognitivePlanner:
    """
    Cognitive Planner proposes an EvidencePlan indicating WHAT evidence is required.
    It does not perform physical retrieval, does not access databases, and does not determine how to fetch evidence.
    """
    def __init__(self, gateway: ModelGatewayProvider):
        self._gateway = gateway

    async def propose_plan(self, query: str, domain_context: str = "generic") -> EvidencePlan:
        # Construct the prompt for the LLM
        system_instruction = "You are a cognitive planning engine. Respond only with valid JSON."
        prompt = f"""
You are the Brain Core Cognitive Planner.
Your task is to analyze the following natural language query and determine what business evidence is needed.
Do NOT write SQL. Do NOT invent database tables. Do NOT execute APIs.
Only propose the semantic evidence requirements.

Query: "{query}"
Domain Context: {domain_context}

Return a JSON object matching this schema:
{{
    "original_intent": "interpreted objective",
    "requirements": [
        {{
            "requirement_id": "req-1",
            "semantic_description": "what facts are needed",
            "necessity": "REQUIRED"
        }}
    ]
}}
"""
        from src.shared.config import settings
        request = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=system_instruction),
                GatewayMessage(role="user", content=prompt)
            ],
            model=settings.stage_r_2_planning_model,
            temperature=0.0
        )
        response = await self._gateway.generate(request)
        response_text = response.content
        
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            data = json.loads(json_str)
            requirements = []
            for req in data.get("requirements", []):
                requirements.append(
                    EvidenceRequirement(
                        requirement_id=req.get("requirement_id", str(uuid.uuid4())),
                        semantic_description=req.get("semantic_description", ""),
                        necessity=req.get("necessity", "REQUIRED"),
                        rationale="Derived from user query."
                    )
                )
            
            plan = EvidencePlan(
                plan_id=str(uuid.uuid4()),
                original_intent=data.get("original_intent", query),
                domain_context=domain_context,
                requirements=requirements
            )
            return plan
        except Exception as e:
            # If parsing fails, fall back to a safe structured output.
            raise ValueError(f"Failed to generate valid EvidencePlan: {e}")

    async def propose_extension(self, package: EvidencePackage, original_query: str) -> EvidencePlanExtension:
        system_instruction = "You are a cognitive planning engine. Respond only with valid JSON."
        prompt = f"""
Review the provided evidence package and the original query. The initial evidence was insufficient.
Propose an extension with new requirements.
Query: {original_query}
Existing Gaps: {[gap.value for gap in package.gaps]}

Return JSON:
{{
    "reason_for_extension": "string",
    "new_requirements": [
        {{
            "requirement_id": "req-ext-1",
            "semantic_description": "what new facts are needed",
            "necessity": "REQUIRED",
            "rationale": "why"
        }}
    ]
}}
"""
        from src.shared.config import settings
        request = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=system_instruction),
                GatewayMessage(role="user", content=prompt)
            ],
            model=settings.stage_r_2_planning_model,
            temperature=0.0
        )
        response = await self._gateway.generate(request)
        response_text = response.content
        
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
                
            data = json.loads(json_str)
            new_reqs = []
            for req in data.get("new_requirements", []):
                new_reqs.append(
                    EvidenceRequirement(
                        requirement_id=req.get("requirement_id", str(uuid.uuid4())),
                        semantic_description=req.get("semantic_description", ""),
                        necessity=req.get("necessity", "REQUIRED"),
                        rationale=req.get("rationale", "Iterative expansion")
                    )
                )
                
            return EvidencePlanExtension(
                parent_plan_id=package.plan_id,
                extension_id=str(uuid.uuid4()),
                new_requirements=new_reqs,
                reason_for_extension=data.get("reason_for_extension", "Initial evidence insufficient")
            )
        except Exception as e:
            raise ValueError(f"Failed to generate valid EvidencePlanExtension: {e}")
