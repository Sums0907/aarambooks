import os
import time
import logging
import httpx
from src.brain_core.gateway.interfaces import (
    ModelGatewayProvider,
    GatewayGenerationRequest,
    GatewayGenerationResponse,
)

logger = logging.getLogger(__name__)

class LiteLLMGatewayAdapter(ModelGatewayProvider):
    """
    Adapter that connects Aaram Brain Core to the LiteLLM Gateway API.
    """
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        from src.shared.config import settings
        self.base_url = (base_url or settings.litellm_base_url).rstrip("/")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", settings.litellm_api_key)
        self.model = model or settings.litellm_model

    async def generate(self, request: GatewayGenerationRequest) -> GatewayGenerationResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        model_to_use = request.model or self.model
        payload = {
            "model": model_to_use,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature if request.temperature > 0.0 else 0.1,
        }
        
        from src.shared.config import settings
        if settings.llm_enforce_json_format:
            payload["format"] = "json"
            
        # if request.max_tokens is not None:
        #     payload["max_tokens"] = request.max_tokens
        # elif settings.llm_routing_max_tokens > 0:
        #     payload["max_tokens"] = settings.llm_routing_max_tokens

        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=300.0)
                response.raise_for_status()
                
                data = response.json()
                choices = data.get("choices", [])
                
                duration = time.time() - start_time
                print(f"[BENCHMARK] LLM Generation took {duration:.2f} seconds", flush=True)
                print(f"[DEBUG] Raw choices: {choices}", flush=True)
                content = choices[0].get("message", {}).get("content") or "" if choices else ""
                print(f"[DEBUG] Raw LiteLLM Content: {content}", flush=True)
                
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                # Use the model name reported back from the proxy, or fallback
                model_used = data.get("model", self.model)
                
                latency_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"GatewayGeneration: model={model_used}, "
                    f"prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, "
                    f"latency_ms={latency_ms:.2f}"
                )
                
                return GatewayGenerationResponse(
                    content=content,
                    model_used=model_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens
                )
        except httpx.HTTPStatusError as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"GatewayGeneration Error: latency_ms={latency_ms:.2f}, error={str(e)}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"GatewayGeneration Error: latency_ms={latency_ms:.2f}, error={str(e)}")
            raise
