import os
import httpx
from src.brain_core.gateway.interfaces import (
    ModelGatewayProvider,
    GatewayGenerationRequest,
    GatewayGenerationResponse,
)

class LiteLLMGatewayAdapter(ModelGatewayProvider):
    """
    Adapter that connects Aaram Brain Core to the LiteLLM Gateway API.
    """
    def __init__(self, base_url: str = "http://localhost:4000", api_key: str = None, model: str = "gemini-3.6-flash"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self.model = model

    async def generate(self, request: GatewayGenerationRequest) -> GatewayGenerationResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            choices = data.get("choices", [])
            content = choices[0].get("message", {}).get("content") or "" if choices else ""
            
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Use the model name reported back from the proxy, or fallback
            model_used = data.get("model", self.model)
            
            return GatewayGenerationResponse(
                content=content,
                model_used=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
