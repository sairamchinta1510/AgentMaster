from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class CritiqueRoundResult(BaseModel):
    round: int
    type: str  # factual_verification | completeness_check | consistency_validation
    passed: bool
    reasoning: str
    unsupported_claims: List[str]


class CritiqueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    round_number: int
    critique_type: str
    verdict: str
    reasoning: str
    unsupported_claims: Optional[List[str]]
    created_at: Optional[str]


class CritiqueVerdict(BaseModel):
    verdict: str  # approved | rejected | needs_human_review
    round_results: List[CritiqueRoundResult]
    overall_confidence: int  # 0-100
