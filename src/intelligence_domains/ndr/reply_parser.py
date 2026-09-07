from typing import Optional, Any
from pydantic import BaseModel, Field
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayMessage
import logging

logger = logging.getLogger(__name__)

class ParsedOutcome(BaseModel):
    intent: str = Field(description="The customer's core intent. Must be one of: RESCHEDULE, RTO_CONFIRMED, ADDRESS_CORRECTION, UNCLEAR")
    reschedule_date: Optional[str] = Field(None, description="If intent is RESCHEDULE, extract the target date in YYYY-MM-DD format if provided, else leave null.")
    address_notes: Optional[str] = Field(None, description="If intent is ADDRESS_CORRECTION, extract any landmark or address details provided.")
    action_to_take: str = Field(description="A short instruction for the operations team for the ATR. E.g. 'Update date to 2026-10-14' or 'Mark as RTO'.")

class CustomerReplyParser:
    def __init__(self, gateway: ModelGatewayProvider):
        self.gateway = gateway
        # Since user is using a local Qwen model, we specify it as the gateway target.
        # However, the LiteLLM gateway abstract base handles routing, so we can pass a generic identifier 
        # or the exact litellm identifier if known. The generic 'default' usually maps to the configured litellm target.
        self.model = "qwen-coder" 

    async def parse_reply(self, raw_message: str) -> ParsedOutcome:
        """
        Uses the ModelGateway to parse an unstructured customer reply into a structured outcome.
        """
        prompt = (
            "You are an e-commerce customer support AI. "
            "A delivery failed and we asked the customer what they want to do. "
            "Analyze the customer's raw reply and extract their intent.\n\n"
            f"Customer Reply: '{raw_message}'\n\n"
            "Extract the intent, date (if any), address notes (if any), and summarize the action to take.\n"
            "Return ONLY a valid JSON object matching the ParsedOutcome schema."
        )

        request = GatewayGenerationRequest(
            messages=[GatewayMessage(role="user", content=prompt)],
            model=None,
            temperature=0.0
        )

        try:
            response = await self.gateway.generate(request)
            
            # Use Pydantic to parse the raw JSON string returned by the LLM
            import json
            raw_json = response.content.strip()
            # Handle markdown code block wrapping
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:-3].strip()
                
            data = json.loads(raw_json)
            parsed = ParsedOutcome(**data)
            logger.info(f"Successfully parsed customer reply into intent: {parsed.intent}")
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to parse customer reply via LLM: {e}")
            return ParsedOutcome(
                intent="UNCLEAR",
                action_to_take="Human review required: LLM parsing failed."
            )
