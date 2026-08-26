import pytest
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayGenerationResponse, GatewayMessage

class MockModelGateway(ModelGatewayProvider):
    async def generate(self, request: GatewayGenerationRequest) -> GatewayGenerationResponse:
        return GatewayGenerationResponse(
            content="mocked response",
            model_used="mock-llm-1",
            prompt_tokens=10,
            completion_tokens=20
        )

@pytest.mark.asyncio
async def test_gateway_interfaces_can_be_mocked():
    gateway = MockModelGateway()
    request = GatewayGenerationRequest(messages=[GatewayMessage(role="user", content="hello")])
    
    response = await gateway.generate(request)
    assert response.content == "mocked response"
    assert response.model_used == "mock-llm-1"

def test_gateway_models_are_frozen():
    msg = GatewayMessage(role="user", content="hello")
    with pytest.raises(Exception):
        msg.role = "system"
