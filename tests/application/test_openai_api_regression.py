import pytest
from fastapi.testclient import TestClient
import json
from unittest.mock import AsyncMock

from src.interfaces.openai_api import router
from fastapi import FastAPI, Request

app = FastAPI()
app.include_router(router)

class MockRabtaOrchestrator:
    async def process_query(self, query, session_id=None, **kwargs):
        class MockRawResponse:
            status = "HUMAN_APPROVAL_REQUIRED"
            message = "I need human approval to proceed."
            render_directives = {
                "action_json": '{"intent": "CREATE_FAMILY"}'
            }
        return MockRawResponse()

@app.middleware("http")
async def add_orchestrator(request: Request, call_next):
    request.app.state.rabta_orchestrator = MockRabtaOrchestrator()
    response = await call_next(request)
    return response

client = TestClient(app)

def test_raw_json_absent_from_chat_response():
    """
    Test that the raw action JSON is NOT appended to the visible assistant message.
    """
    payload = {
        "model": "rabta",
        "messages": [
            {"role": "user", "content": "Add a Midnight Blue bedsheet, king size"}
        ],
        "stream": False
    }
    
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    message_content = data["choices"][0]["message"]["content"]
    
    assert "I need human approval to proceed." in message_content
    # The raw JSON block should NOT be appended to the visible message text
    assert "```json" not in message_content
    assert '{"intent": "CREATE_FAMILY"}' not in message_content
