import json
from typing import Dict, Any, List
from src.shared.conversational_contracts import ConversationalUnderstanding
from src.shared.requirement_classification_contracts import (
    RequirementClass,
    ClassifiedComponent,
    ClassifiedRequirement
)
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage

class RequirementClassifier:
    """
    RABTA R-2: Requirement Classification.
    This module uses an LLM to evaluate the R-1 ConversationalUnderstanding and assign 
    a RequirementClass to each of its components based strictly on conversational context.
    It does NOT invent missing fields or query CEM capabilities.
    """

    def __init__(self, gateway: ModelGatewayProvider):
        self._gateway = gateway
        self._system_prompt = """You are the Rabta R-2 Requirement Classifier for Aaram Brain Core.
Your ONLY job is to classify the semantic components of a user's conversational request.

RULES:
1. You will receive a JSON representing the R-1 ConversationalUnderstanding.
2. You must classify EACH entity, attribute, condition, and scope present in the JSON into one of the following classes:
   - MANDATORY: Fundamentally required to answer the conversational intent.
   - OPTIONAL: Adds precision, but the core conversational intent survives without it.
   - DERIVABLE: It is a contextual reference (e.g. "the second one", "that warehouse").
   - AMBIGUOUS: The conversational phrasing itself has multiple materially conflicting meanings.
   - UNRESOLVED: The conversational intent is so sparse a conceptual question cannot be formed.

3. STRICT PROHIBITIONS:
   - DO NOT invent missing concepts (e.g., if a warehouse is not mentioned, DO NOT invent a warehouse component).
   - DO NOT use the BROADENABLE classification. (This is reserved for later execution phases).
   - DO NOT inspect or assume database schemas, SQL, UUIDs, or CEM capabilities.
   - DO NOT determine whether execution is physically possible.
   - Evaluate attributes (like colors, sizes) based on their conversational role. They are not automatically OPTIONAL.

You must return a raw JSON array of objects (NO markdown formatting, just raw JSON).
Each object must have:
{
  "component_reference": "<original_expression of the component>",
  "classification": "<MANDATORY|OPTIONAL|DERIVABLE|AMBIGUOUS|UNRESOLVED>",
  "reason": "<short conversational justification>"
}

If the entire query is fundamentally ambiguous or unresolved, you may include an object with "component_reference": "GLOBAL".

CRITICAL REQUIREMENT:
You must output ONLY a valid JSON array. Do not include markdown tags like ```json. Do not include any explanations, preamble, or conversational text. Start directly with [ and end with ].
"""

    async def classify(self, understanding: ConversationalUnderstanding) -> ClassifiedRequirement:
        # Construct the representation of the understanding
        components_to_classify = []
        
        for entity in understanding.entities:
            components_to_classify.append({"type": "entity", "expression": entity.original_expression, "source": entity.source.value})
        
        for attr in understanding.attributes:
            components_to_classify.append({"type": "attribute", "name": attr.attribute_name, "expression": attr.original_expression})
            
        for cond in understanding.conditions:
            components_to_classify.append({"type": "condition", "target": cond.attribute_or_entity, "operator": cond.operator.value, "value": cond.value})
            
        if understanding.scope:
            components_to_classify.append({"type": "scope", "expression": understanding.scope.scope_expression})
            
        for crit in understanding.user_supplied_criteria:
            components_to_classify.append({"type": "user_supplied_criteria", "expression": crit})

        if not components_to_classify:
            # Nothing to classify, likely unresolved global
            return ClassifiedRequirement(
                understanding=understanding,
                component_classifications=[],
                global_classification=RequirementClass.UNRESOLVED
            )

        user_content = json.dumps({
            "intent": understanding.intent.value,
            "desired_outcome": understanding.desired_outcome,
            "components": components_to_classify
        }, indent=2)

        from src.shared.config import settings
        request = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=self._system_prompt),
                GatewayMessage(role="user", content=user_content)
            ],
            model=settings.stage_r_2_planning_model,
            temperature=0.0
        )

        response = await self._gateway.generate(request)
        
        try:
            # Clean possible markdown if model ignored the instruction
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            classifications_data = json.loads(content)
            
            classified_components = []
            global_class = None
            
            for item in classifications_data:
                ref = item.get("component_reference")
                cls = item.get("classification")
                reason = item.get("reason", "")
                
                if not ref or not cls:
                    continue
                    
                # Map to enum
                try:
                    req_class = RequirementClass(cls)
                except ValueError:
                    req_class = RequirementClass.MANDATORY # fallback
                    
                if ref == "GLOBAL":
                    global_class = req_class
                else:
                    classified_components.append(
                        ClassifiedComponent(
                            component_reference=ref,
                            classification=req_class,
                            reason=reason
                        )
                    )
                    
            return ClassifiedRequirement(
                understanding=understanding,
                component_classifications=classified_components,
                global_classification=global_class
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback for parsing errors: everything is mandatory
            fallback_components = []
            for comp in components_to_classify:
                ref = comp.get("expression") or comp.get("value") or str(comp)
                if isinstance(ref, dict):
                    ref = str(ref)
                fallback_components.append(
                    ClassifiedComponent(
                        component_reference=str(ref),
                        classification=RequirementClass.MANDATORY,
                        reason="Fallback due to classification parsing error."
                    )
                )
                
            return ClassifiedRequirement(
                understanding=understanding,
                component_classifications=fallback_components,
                global_classification=None
            )
