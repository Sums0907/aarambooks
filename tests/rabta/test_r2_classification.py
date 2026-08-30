import pytest
import json
from src.shared.conversational_contracts import (
    ConversationalUnderstanding, ConversationalIntent, InformationSource, 
    SemanticEntityReference, SemanticAttribute, SemanticScope
)
from src.shared.requirement_classification_contracts import RequirementClass
from src.brain_core.classification.classifier import RequirementClassifier
from src.brain_core.gateway.interfaces import ModelGatewayProvider, GatewayGenerationRequest, GatewayGenerationResponse

class MockGatewayProvider(ModelGatewayProvider):
    def __init__(self, raw_json_response: str):
        self.raw_json_response = raw_json_response
        self.last_request = None

    async def generate(self, request: GatewayGenerationRequest) -> GatewayGenerationResponse:
        self.last_request = request
        return GatewayGenerationResponse(
            content=self.raw_json_response,
            model_used="mock-model",
            prompt_tokens=10,
            completion_tokens=10
        )

@pytest.mark.asyncio
async def test_explicit_core_entity():
    understanding = ConversationalUnderstanding(
        original_query="Give me stock of Blush Bloom",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="Blush Bloom", source=InformationSource.EXPLICIT)
        ]
    )
    
    mock_response = json.dumps([
        {
            "component_reference": "Blush Bloom",
            "classification": "MANDATORY",
            "reason": "Core subject of retrieve intent."
        }
    ])
    
    classifier = RequirementClassifier(MockGatewayProvider(mock_response))
    classified_req = await classifier.classify(understanding)
    
    # 1. R-1 output remains unchanged
    assert classified_req.understanding == understanding
    # 2. Classification is parsed
    assert len(classified_req.component_classifications) == 1
    assert classified_req.component_classifications[0].component_reference == "Blush Bloom"
    assert classified_req.component_classifications[0].classification == RequirementClass.MANDATORY
    # 3. No global default
    assert classified_req.global_classification is None

@pytest.mark.asyncio
async def test_explicit_filtering_attributes_and_no_hallucinations():
    understanding = ConversationalUnderstanding(
        original_query="Give me stock of blue king bedsheets",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="bedsheets")
        ],
        attributes=[
            SemanticAttribute(attribute_name="color", original_expression="blue"),
            SemanticAttribute(attribute_name="size", original_expression="king")
        ]
    )
    
    mock_response = json.dumps([
        {
            "component_reference": "bedsheets",
            "classification": "MANDATORY",
            "reason": "Core entity"
        },
        {
            "component_reference": "blue",
            "classification": "OPTIONAL",
            "reason": "Conversational preference"
        },
        {
            "component_reference": "king",
            "classification": "OPTIONAL",
            "reason": "Conversational preference"
        }
    ])
    
    classifier = RequirementClassifier(MockGatewayProvider(mock_response))
    classified_req = await classifier.classify(understanding)
    
    assert len(classified_req.component_classifications) == 3
    # Verify no missing concepts are invented (like a warehouse)
    refs = [c.component_reference for c in classified_req.component_classifications]
    assert "warehouse" not in refs
    assert "UUID" not in refs

@pytest.mark.asyncio
async def test_contextual_derivable_references():
    understanding = ConversationalUnderstanding(
        original_query="How much stock does the second one have?",
        intent=ConversationalIntent.RETRIEVE,
        entities=[
            SemanticEntityReference(original_expression="the second one", source=InformationSource.CONTEXTUAL)
        ]
    )
    
    mock_response = json.dumps([
        {
            "component_reference": "the second one",
            "classification": "DERIVABLE",
            "reason": "Refers to context"
        }
    ])
    
    classifier = RequirementClassifier(MockGatewayProvider(mock_response))
    classified_req = await classifier.classify(understanding)
    
    assert classified_req.component_classifications[0].classification == RequirementClass.DERIVABLE

@pytest.mark.asyncio
async def test_conversational_ambiguity():
    understanding = ConversationalUnderstanding(
        original_query="Show me the records",
        intent=ConversationalIntent.SEARCH,
        entities=[
            SemanticEntityReference(original_expression="records")
        ]
    )
    
    mock_response = json.dumps([
        {
            "component_reference": "records",
            "classification": "AMBIGUOUS",
            "reason": "Unclear which records"
        }
    ])
    
    classifier = RequirementClassifier(MockGatewayProvider(mock_response))
    classified_req = await classifier.classify(understanding)
    
    assert classified_req.component_classifications[0].classification == RequirementClass.AMBIGUOUS

@pytest.mark.asyncio
async def test_truly_unresolved_conversational_requests():
    understanding = ConversationalUnderstanding(
        original_query="give me",
        intent=ConversationalIntent.UNKNOWN
    )
    
    # If the LLM assigns GLOBAL UNRESOLVED
    mock_response = json.dumps([
        {
            "component_reference": "GLOBAL",
            "classification": "UNRESOLVED",
            "reason": "No intent or entity."
        }
    ])
    
    classifier = RequirementClassifier(MockGatewayProvider(mock_response))
    classified_req = await classifier.classify(understanding)
    
    assert classified_req.global_classification == RequirementClass.UNRESOLVED
    assert len(classified_req.component_classifications) == 0

@pytest.mark.asyncio
async def test_empty_components_automatically_unresolved():
    understanding = ConversationalUnderstanding(
        original_query="hello",
        intent=ConversationalIntent.UNKNOWN
    )
    
    # Without calling LLM, if components_to_classify is empty, it returns UNRESOLVED
    classifier = RequirementClassifier(MockGatewayProvider("[]"))
    classified_req = await classifier.classify(understanding)
    
    assert classified_req.global_classification == RequirementClass.UNRESOLVED
