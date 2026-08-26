import pytest
from src.brain_core.decision.interfaces import DecisionAlternative, DecisionRecommendation, DecisionAnalysisRequest

def test_decision_structures():
    alt1 = DecisionAlternative(id="alt1", description="Option 1", confidence=0.8, reasoning="Because X", expected_outcomes=["A"])
    alt2 = DecisionAlternative(id="alt2", description="Option 2", confidence=0.4, reasoning="Because Y", expected_outcomes=["B"])
    
    rec = DecisionRecommendation(
        recommended_alternative_id="alt1",
        alternatives_considered=[alt1, alt2],
        justification="Option 1 is better"
    )
    
    assert rec.recommended_alternative_id == "alt1"
    assert len(rec.alternatives_considered) == 2

def test_decision_models_are_frozen():
    alt = DecisionAlternative(id="alt", description="desc", confidence=1.0, reasoning="reason", expected_outcomes=[])
    with pytest.raises(Exception):
        alt.confidence = 0.5
