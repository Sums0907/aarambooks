import httpx
import logging
from typing import Dict, Any
from src.shared.config import settings
from src.brain_core.action_engine.contracts import ActionRequest

logger = logging.getLogger(__name__)

class ExotelVoiceBotAdapter:
    """
    Physical execution adapter for Exotel Native VoiceBot.
    Implements POST /v1/accounts/{accountsid}/calls/connect to trigger outbound flow.
    """
    def __init__(self):
        self.api_key = settings.exotel_api_key
        self.api_token = settings.exotel_api_token
        self.subdomain = settings.exotel_subdomain
        self.account_sid = settings.exotel_account_sid
        self.caller_id = settings.exotel_caller_id
        self.flow_url = settings.exotel_voicebot_flow_url
        
        self.base_url = f"https://{self.subdomain}/v1/Accounts/{self.account_sid}"

    async def dispatch_call(self, action_request: ActionRequest, engagement_id: str) -> Dict[str, Any]:
        """
        Triggers an individual outbound call via Exotel Connect Voice AI API.
        
        CRITICAL SAFETY RULE: 
        Outbound call creation is retry-unsafe because Exotel does not provide a verified 
        idempotency-key mechanism for this API. Automatic blind retries on network timeouts 
        or 5xx errors risk creating duplicate physical calls to the customer.
        We fail fast and explicitly classify the error.
        """
        if not self.account_sid or not self.api_key or not self.flow_url:
            raise ValueError("Exotel credentials or flow URL not fully configured.")

        customer_phone = action_request.parameters.get("customer_phone")
        
        if getattr(settings, "test_phone_override", ""):
            customer_phone = settings.test_phone_override
            logger.info(f"TEST MODE: Overriding customer phone to {customer_phone}")
            
        if not customer_phone:
            raise ValueError("Customer phone number missing in parameters.")

        endpoint = f"{self.base_url}/Calls/connect.json"
        
        # Pass correlation IDs. Authentication is handled by Bearer token in the VoiceBot UI.
        base_custom_field = f"{engagement_id}|{action_request.action_request_id}"
        
        payload = {
            "From": customer_phone,
            "To": self.caller_id,
            "CallerId": self.caller_id,
            "Url": self.flow_url,
            "CustomField": base_custom_field
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    auth=(self.api_key, self.api_token),
                    data=payload,
                    timeout=10.0
                )
            
            response.raise_for_status()
            
            data = response.json()
            call_info = data.get("Call", {})
            
            return {
                "call_id": call_info.get("Sid"),
                "status": call_info.get("Status")
            }
            
        except httpx.TimeoutException as e:
            logger.error(f"Exotel outbound timeout for engagement {engagement_id}. Retry-unsafe: DO NOT auto-retry.")
            raise RuntimeError(f"Exotel timeout: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                logger.error(f"Exotel rate limit (429) for engagement {engagement_id}.")
            elif status >= 500:
                logger.error(f"Exotel server error ({status}) for engagement {engagement_id}. Retry-unsafe.")
            else:
                logger.error(f"Exotel permanent client error ({status}) for engagement {engagement_id}.")
            raise RuntimeError(f"Exotel HTTP {status}: {e.response.text}") from e
        except httpx.RequestError as e:
            logger.error(f"Exotel network failure for engagement {engagement_id}. Retry-unsafe.")
            raise RuntimeError(f"Exotel network error: {str(e)}") from e
