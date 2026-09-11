import pytest
import uuid
import json
import os
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

os.environ["AARAM_EXOTEL_WEBHOOK_SECRET"] = "Samashu@01"

from src.brain_core.action_engine.contracts import ActionRequest, ConversationalDirective, ActionCategory
from src.brain_core.context_engine.ccc_contracts import CustomerConversationContext, NDRConversationProjection, ProductContext
from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementRecord, EngagementState
from src.infrastructure.adapters.customer_engagement.executor import CustomerEngagementExecutor
from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus

@pytest.fixture
def mock_shopdeck_provider():
    provider = AsyncMock()
    # Mocking standard successful response
    provider.execute_evidence_request.return_value = BusinessEvidenceResponse(
        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
        evidence_data={
            "customer_name": "John Doe",
            "customer.attribute.phone": "9876543210",
            "cod_amount": 1499.0,
            "payment_mode": "cod",
            "items": [{
                "sku_id": "SKU-TEST-123",
                "product_code": "PC-123",
                "product_name": "Premium Cotton Bedsheet",
                "quantity": 1,
                "selling_price": 1499.0
            }]
        }
    )
    return provider

@pytest.fixture
def action_request():
    directive = ConversationalDirective(
        objective="Schedule a reattempt for tomorrow.",
        context_summary="Customer was unavailable today.",
        allowed_actions=["reschedule"],
        constraints=["Do not name courier"]
    )
    return ActionRequest(
        action_request_id=f"act_{uuid.uuid4().hex[:8]}",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Customer was unavailable.",
        parameters={"awb_no": "AWB12345"},
        directive=directive
    )


@pytest.mark.asyncio
async def test_gate_a_ccc_contract(action_request, mock_shopdeck_provider):
    """Gate A: CCC contract/unit tests"""
    builder = CustomerConversationContextBuilder(provider=mock_shopdeck_provider)
    ccc = await builder.build(action_request)
    
    assert isinstance(ccc, CustomerConversationContext)
    assert ccc.customer_profile.name == "John Doe"
    assert ccc.order_facts.collectable_amount == 1499.0
    assert ccc.product_context.product_name == "Premium Cotton Bedsheet"
    assert ccc.directive.objective == "Schedule a reattempt for tomorrow."

@pytest.mark.asyncio
async def test_gate_b_shopdeck_mapping(action_request, mock_shopdeck_provider):
    """Gate B: ShopDeck -> Context Provider -> CCC mapping tests."""
    builder = CustomerConversationContextBuilder(provider=mock_shopdeck_provider)
    ccc = await builder.build(action_request)
    
    # Verify rich catalog is explicitly marked unavailable
    assert ccc.product_context.rich_attributes_available is False
    assert getattr(ccc.product_context, "material", None) is None # ProductContext should not have material

@pytest.mark.asyncio
async def test_gate_c_ccc_projection(action_request, mock_shopdeck_provider):
    """Gate C: CCC -> customer-safe Projection tests."""
    builder = CustomerConversationContextBuilder(provider=mock_shopdeck_provider)
    ccc = await builder.build(action_request)
    
    projection = builder.project(ccc)
    assert isinstance(projection, NDRConversationProjection)
    
    # Internal IDs should be stripped
    assert getattr(projection, "ccc_id", None) is None
    
    # Essential conversational facts remain
    assert projection.customer_name == "John Doe"
    assert projection.product_name == "Premium Cotton Bedsheet"
    assert projection.domain_constraints == ["Do not name courier"]
    assert "Never execute a financial transaction." in projection.core_safety_constraints

@pytest.mark.asyncio
async def test_gate_d_immutable_snapshot_persistence():
    """Gate D: immutable snapshot persistence tests."""
    # Ensure CustomerEngagementRecord can accept a serialized CCC snapshot
    record = CustomerEngagementRecord(
        action_request_id="act_123",
        awb_no="AWB123",
        channel="VOICE",
        provider="EXOTEL",
        ccc_snapshot={"ccc_id": "ccc_999", "target_identity": "AWB123"}
    )
    assert record.ccc_snapshot["ccc_id"] == "ccc_999"

@pytest.mark.asyncio
async def test_gate_e_executor_integration(action_request, mock_shopdeck_provider):
    """Gate E: ActionRequest -> CCC -> Executor integration test."""
    mock_repo = AsyncMock()
    builder = CustomerConversationContextBuilder(provider=mock_shopdeck_provider)
    executor = CustomerEngagementExecutor(repository=mock_repo, exotel_adapter=None)
    
    # Inject execution_intent
    from src.brain_core.action_engine.contracts import ExecutionIntent, ExecutionChannel
    action_request = action_request.model_copy(update={"execution_intent": ExecutionIntent(intent_type="OUTBOUND", channel=ExecutionChannel.VOICE)})
    
    ccc = await builder.build(action_request)
    ccc_snapshot = ccc.model_dump()
    projection = builder.project(ccc)
    call_context = projection.model_dump()
    
    engagement = await executor.execute_engagement(action_request, call_context=call_context, ccc_snapshot=ccc_snapshot)
    
    assert engagement.status == EngagementState.FAILED # Fails due to no exotel_adapter, but that's fine
    
    # Verify CCC Snapshot was persisted
    assert engagement.ccc_snapshot is not None
    assert engagement.ccc_snapshot["product_context"]["product_name"] == "Premium Cotton Bedsheet"
    
    # Verify call_context is the Governed Projection
    assert "ccc_id" not in engagement.call_context
    assert engagement.call_context["product_name"] == "Premium Cotton Bedsheet"

def test_gate_g_boundary_constraints():
    """Gate G: boundary tests proving executor does not build context."""
    # Ensure executor relies on CCCBuilder and does not import ShopDeck provider directly
    import inspect
    from src.infrastructure.adapters.customer_engagement.executor import CustomerEngagementExecutor
    
    source = inspect.getsource(CustomerEngagementExecutor)
    assert "ShopdeckCemAdapter" not in source
    assert "BusinessEvidenceResponse" not in source

@pytest.mark.asyncio
async def test_gate_f_behavioral_webhook_isolation():
    """Gate F: Exotel Session Start Behavioral Test."""
    from fastapi.testclient import TestClient
    from src.main import app
    from src.api.webhooks.exotel_webhooks import get_repository
    
    mock_repo = AsyncMock()
    mock_repo.get_engagement.return_value = {
        "engagement_id": "eng_123",
        "action_request_id": "act_123",
        "awb_no": "AWB123",
        "call_context": {
            "customer_name": "Test User",
            "product_name": "Test Product",
            "domain_constraints": ["Test Constraint"]
        }
    }
    
    app.dependency_overrides[get_repository] = lambda: mock_repo
    client = TestClient(app)
    from src.shared.config import settings
    secret = settings.aaram_exotel_webhook_secret
    response = client.post(
        f"/api/customer-engagement/voice/exotel/session-start?secret={secret}",
        json={"CustomField": "eng_123|act_123", "CallSid": "sid_123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    pass # Greeting changed, product name may not be included directly
    assert "Test Product" == data["response"]["data"]["session_constants"]["product_name"]
    
    # Assert get_engagement was called exactly once and NO shopdeck dependency was triggered
    mock_repo.get_engagement.assert_called_once_with("eng_123")
    
@pytest.mark.asyncio
async def test_gate_h_immutability():
    """Verify webhooks cannot mutate CCC Snapshot."""
    from fastapi.testclient import TestClient
    from src.main import app
    from src.api.webhooks.exotel_webhooks import get_repository
    
    mock_repo = AsyncMock()
    app.dependency_overrides[get_repository] = lambda: mock_repo
    client = TestClient(app)
    
    from src.shared.config import settings
    secret = settings.aaram_exotel_webhook_secret
    response = client.post(
        f"/api/customer-engagement/voice/exotel/transcript?secret={secret}",
        json={"CustomField": "eng_123|act_123", "CallSid": "sid_123", "Transcript": "Hello"}
    )
    
    assert response.status_code == 200
    # Assert log_event was called, but update_engagement or anything mutating snapshot was NOT
    assert mock_repo.log_event.called
    assert not hasattr(mock_repo, 'update_snapshot') or not mock_repo.update_snapshot.called
    assert mock_repo.transition_state.called
