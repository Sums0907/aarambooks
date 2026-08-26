from pydantic import BaseModel, ConfigDict
from typing import List

class DecisionAlternative(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    description: str
    confidence: float
    reasoning: str
    expected_outcomes: List[str]

class DecisionRecommendation(BaseModel):
    """
    Pure logical structure representing an intelligence recommendation.
    The Decision Engine supports business decisions without overriding operational truth.
    """
    model_config = ConfigDict(frozen=True)
    recommended_alternative_id: str
    alternatives_considered: List[DecisionAlternative]
    justification: str

class DecisionAnalysisRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision_context: str
    constraints: List[str]
