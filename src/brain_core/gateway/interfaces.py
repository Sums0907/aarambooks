from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class GatewayMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str
    content: str

class GatewayGenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    messages: List[GatewayMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class GatewayGenerationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int

class ModelGatewayProvider(ABC):
    """
    Abstract interface for Aaram Brain Core LLM generation.
    Decouples reasoning capabilities from underlying vendor SDKs and infrastructure.
    """
    
    @abstractmethod
    async def generate(self, request: GatewayGenerationRequest) -> GatewayGenerationResponse:
        """Execute a logical prompt generation request through the gateway."""
        pass
