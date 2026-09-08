import pytest
from src.api.webhooks.exotel_webhooks import build_session_constants
from src.brain_core.context_engine.ccc_contracts import (
    CustomerConversationContext,
    CustomerContext,
    OrderContext,
    ProductContext
)
from src.brain_core.action_engine.contracts import ConversationalDirective, ConversationMissionContract
from pydantic import BaseModel

def test_session_constants_engagement_id_is_scalar():
    """
    Proves that build_session_constants returns a scalar string for engagement_id,
    and does not serialize a Pydantic model into it.
    """
    mission = ConversationMissionContract(
        conversation_mission="NDR_RECOVERY",
        why_this_call="A delivery attempt failed.",
        primary_objective="Capture preference.",
        success_condition="Success.",
        initial_state="INTRODUCE_REASON",
        allowed_actions=["capture_customer_delivery_preference"],
        allowed_next_states=["RESOLVING"],
        conversation_priority="Priority.",
        return_to_mission="RETURN_TO_NDR"
    )
    
    directive = ConversationalDirective(
        objective="Capture preference.",
        context_summary="Summary.",
        allowed_actions=["capture_customer_delivery_preference"],
        constraints=["None"],
        mission=mission
    )
    
    ccc = CustomerConversationContext(
        ccc_id="ccc_test",
        target_identity="AWB-123",
        customer_profile=CustomerContext(name="Rahul", phone="9999999999"),
        order_facts=OrderContext(
            awb_no="AWB-123",
            collectable_amount=799.0,
            payment_mode="cod",
            actual_item_price=799.0,
            order_quantity=1,
            past_delivery_attempts=1,
        ),
        product_context=ProductContext(product_name="Cotton Bedsheet"),
        directive=directive
    )
    
    from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
    builder = CustomerConversationContextBuilder(provider=None)
    projection = builder.project(ccc)
    
    # Simulate exactly how the production exotel_webhooks.py calls build_session_constants
    engagement_id = "eng_prod123"
    action_request_id = "act_456"
    
    # In production, engagement['call_context'] holds the projection
    engagement = {
        "call_context": projection.model_dump(),
        "awb_no": "AWB-123"
    }
    
    session_constants = build_session_constants(
        engagement_id=engagement_id,
        action_request_id=action_request_id,
        engagement=engagement
    )
    
    # Assertions
    assert session_constants["engagement_id"] == "eng_prod123", "engagement_id must be a scalar string matching the ID"
    assert session_constants["action_request_id"] == "act_456"
    assert session_constants["awb_no"] == "AWB-123"
    
    # Prove that the ID does not contain any object/model serialization (like 'customer_name=...')
    assert "customer_name" not in session_constants["engagement_id"], "engagement_id must not serialize the model!"
    
    # Ensure mission constants were properly extracted
    assert session_constants["mission_initial_state"] == "INTRODUCE_REASON"
    assert session_constants["customer_name"] == "Rahul"
    assert session_constants["product_name"] == "Cotton Bedsheet"
