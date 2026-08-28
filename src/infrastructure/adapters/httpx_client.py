import httpx
from typing import Dict, Any, Optional
from src.infrastructure.context_capability_gateway import HttpClient, HttpResponse

class HttpxClientAdapter(HttpClient):
    """
    Domain-neutral HTTP client adapter for the generic ContextCapabilityGateway.
    Handles network execution, timeouts, and translates httpx responses to the generic HttpResponse.
    """
    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout

    async def post(self, url: str, headers: Dict[str, str], json_payload: Dict[str, Any]) -> HttpResponse:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=json_payload)
                
                # Check for 5xx server errors at the transport level
                if response.status_code >= 500:
                    return HttpResponse(
                        status_code=response.status_code,
                        text_data=response.text,
                        error_message=f"Transport error (HTTP {response.status_code})"
                    )
                
                # Try parsing JSON for 2xx/4xx
                json_data = None
                text_data = response.text
                try:
                    json_data = response.json()
                except Exception:
                    pass

                return HttpResponse(
                    status_code=response.status_code,
                    json_data=json_data,
                    text_data=text_data
                )
        except httpx.TimeoutException:
            return HttpResponse(
                status_code=504,
                error_message="Transport exception: Request timed out"
            )
        except httpx.RequestError as e:
            return HttpResponse(
                status_code=502,
                error_message=f"Transport exception: Network error occurred - {str(e)}"
            )
        except Exception as e:
            return HttpResponse(
                status_code=500,
                error_message=f"Transport exception: {str(e)}"
            )
