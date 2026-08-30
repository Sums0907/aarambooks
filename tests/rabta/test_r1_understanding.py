import pytest
import json
from src.shared.conversational_contracts import (
    ConversationalUnderstanding, ConversationalIntent, InformationSource, 
    SemanticEntityReference, SemanticAttribute, SemanticScope, SemanticCondition, SemanticOperator
)

def test_basic_intent():
    # Test that ConversationalUnderstanding can represent "Give me stock of SKU X"
    cu = ConversationalUnderstanding(
        original_query="Give me stock of SKU X",
        intent=ConversationalIntent.RETRIEVE,
        domain="INVENTORY",
        entities=[
            SemanticEntityReference(original_expression="SKU X", source=InformationSource.EXPLICIT)
        ],
        desired_outcome="stock"
    )
    assert cu.intent == ConversationalIntent.RETRIEVE
    assert cu.entities[0].original_expression == "SKU X"

def test_natural_name_and_typo():
    cu = ConversationalUnderstanding(
        original_query="Give me stock of Blush Blom",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="Blush Blom", source=InformationSource.EXPLICIT)
        ]
    )
    # The typo MUST be preserved, not resolved
    assert cu.entities[0].original_expression == "Blush Blom"

def test_attributes_and_operators():
    cu = ConversationalUnderstanding(
        original_query="Show products with stock greater than 50",
        intent=ConversationalIntent.SEARCH,
        conditions=[
            SemanticCondition(
                attribute_or_entity="stock",
                operator=SemanticOperator.GREATER_THAN,
                value=50,
                source=InformationSource.EXPLICIT
            )
        ]
    )
    assert cu.conditions[0].operator == SemanticOperator.GREATER_THAN
    assert cu.conditions[0].value == 50

def test_unspecified_scope():
    cu = ConversationalUnderstanding(
        original_query="Give me stock of SKU X",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="SKU X")
        ]
    )
    # R-1 must not default this to mandatory warehouse scope
    assert cu.scope is None

def test_conversational_context():
    cu = ConversationalUnderstanding(
        original_query="How much stock does it have?",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="it", source=InformationSource.CONTEXTUAL)
        ]
    )
    assert cu.entities[0].source == InformationSource.CONTEXTUAL
    assert cu.entities[0].original_expression == "it"

def test_user_supplied_criteria():
    cu = ConversationalUnderstanding(
        original_query="Show me low stock, low stock means below 50 units",
        intent=ConversationalIntent.SEARCH,
        user_supplied_criteria=["low stock means below 50 units"]
    )
    assert len(cu.user_supplied_criteria) == 1

def test_partial_product_name():
    cu = ConversationalUnderstanding(
        original_query="stock for blush",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="blush", source=InformationSource.EXPLICIT)
        ]
    )
    assert cu.entities[0].original_expression == "blush"

def test_multiple_attributes():
    cu = ConversationalUnderstanding(
        original_query="blue king bedsheets",
        intent=ConversationalIntent.SEARCH,
        attributes=[
            SemanticAttribute(attribute_name="color", original_expression="blue"),
            SemanticAttribute(attribute_name="size", original_expression="king")
        ],
        entities=[
            SemanticEntityReference(original_expression="bedsheets")
        ]
    )
    assert len(cu.attributes) == 2

def test_explicit_warehouse_scope():
    cu = ConversationalUnderstanding(
        original_query="stock in Delhi warehouse",
        intent=ConversationalIntent.RETRIEVE,
        scope=SemanticScope(scope_expression="Delhi warehouse")
    )
    assert cu.scope.scope_expression == "Delhi warehouse"

def test_broad_request():
    cu = ConversationalUnderstanding(
        original_query="Show me all stock",
        intent=ConversationalIntent.RETRIEVE,
        desired_outcome="all stock"
    )
    assert cu.desired_outcome == "all stock"
    assert not cu.entities

def test_unknown_looking_entity():
    cu = ConversationalUnderstanding(
        original_query="stock for XYZ123ABC",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="XYZ123ABC")
        ]
    )
    assert cu.entities[0].original_expression == "XYZ123ABC"

def test_compound_request():
    cu = ConversationalUnderstanding(
        original_query="stock for Blush Bloom in Delhi and sales in Mumbai",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="Blush Bloom")
        ],
        scope=SemanticScope(scope_expression="Delhi and Mumbai")
    )
    assert cu.intent == ConversationalIntent.RETRIEVE
