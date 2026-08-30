import json
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel
from typing_extensions import Protocol

from src.shared.context_contracts.provider import (
    ContextCapabilityProvider,
    ContextRetrievalStatus,
    ContextCapabilityResult
)
from src.shared.context_contracts.capability import CapabilityURN
from src.shared.semantic_resolution_contracts import ResolvedSemanticRequirement

class GatewayConfiguration(Protocol):
    """Configuration mapping URNs to Business System endpoints."""
    def get_endpoint(self, urn: CapabilityURN) -> Optional[str]:
        ...

class HttpResponse(BaseModel):
    status_code: int
    json_data: Optional[Dict[str, Any]] = None
    text_data: Optional[str] = None
    error_message: Optional[str] = None

class HttpClient(Protocol):
    """Generic abstract HTTP client to allow injection and easy testing."""
    async def post(self, url: str, headers: Dict[str, str], json_payload: Dict[str, Any]) -> HttpResponse:
        ...

class ContextCapabilityGateway(ContextCapabilityProvider):
    """
    The generic Brain-side transport socket.
    It performs NO domain interpretation. It simply serializes the generic requirement,
    transmits it to the configured external endpoint, and deserializes the opaque response.
    """
    def __init__(self, config: GatewayConfiguration, http_client: HttpClient):
        self._config = config
        self._http_client = http_client

    async def invoke_capability(
        self, 
        capability_urn: CapabilityURN, 
        requirement: ResolvedSemanticRequirement,
        authorization_context: str
    ) -> ContextCapabilityResult:
        
        endpoint = self._config.get_endpoint(capability_urn)
        if not endpoint:
            return ContextCapabilityResult(
                status=ContextRetrievalStatus.ERROR,
                error_message=f"No endpoint configured for URN: {capability_urn}",
                provenance_metadata=None # type: ignore (handled by orchestrator if error)
            )
            
        correlation_id = str(uuid.uuid4())
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {authorization_context}" if not authorization_context.startswith("Bearer") else authorization_context,
            "X-Correlation-ID": correlation_id
        }
        
        # Translate to physical API schema
        req_dict = requirement.model_dump(mode='json')
        orig_req = req_dict.get("original_requirement", {})
        if "semantic_description" in orig_req:
            orig_req["semantic_intent"] = orig_req.pop("semantic_description")
            
        payload = {
            "capability_urn": capability_urn,
            "requirement": req_dict
        }
        
        try:
            # Transport Execution
            print(f"\n[GATEWAY DEBUG] Sending to {endpoint} with payload: {json.dumps(payload)}", flush=True)
            response = await self._http_client.post(endpoint, headers=headers, json_payload=payload)
            print(f"[GATEWAY DEBUG] Received status {response.status_code}: {response.text_data}\n", flush=True)
            
            # Transport Failure
            if response.status_code >= 400:
                print(f"[GATEWAY DEBUG] Returning ERROR due to HTTP {response.status_code}", flush=True)
                return ContextCapabilityResult(
                    status=ContextRetrievalStatus.ERROR,
                    error_message=f"Transport error (HTTP {response.status_code}): {response.text_data}",
                    provenance_metadata=None # type: ignore
                )
                
            # Business System Evaluation
            if not response.json_data:
                return ContextCapabilityResult(
                    status=ContextRetrievalStatus.ERROR,
                    error_message=f"Malformed response from provider (HTTP {response.status_code})",
                    provenance_metadata=None # type: ignore
                )
                
            result_data = response.json_data
            status_str = result_data.get("status", "ERROR")
            
            # Map string back to Enum, defaulting to ERROR if malformed
            try:
                mapped_status = ContextRetrievalStatus(status_str)
            except ValueError:
                mapped_status = ContextRetrievalStatus.ERROR
                
            return ContextCapabilityResult(
                status=mapped_status,
                data=result_data.get("data"),
                provenance_metadata=result_data.get("provenance_metadata"),
                error_message=result_data.get("error_message")
            )
            
        except Exception as e:
            # Catch arbitrary transport exceptions (timeouts, connection resets)
            return ContextCapabilityResult(
                status=ContextRetrievalStatus.ERROR,
                error_message=f"Transport exception: {str(e)}",
                provenance_metadata=None # type: ignore
            )
