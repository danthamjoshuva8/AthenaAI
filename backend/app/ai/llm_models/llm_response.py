from typing import List, Optional

from pydantic import BaseModel


class LLMResponse(BaseModel):
    decision: str
    confidence: int

    reasoning: str

    risks: List[str] = []

    strengths: List[str] = []

    weaknesses: List[str] = []

    recommendation: Optional[str] = None

    news_impact: Optional[str] = None

    fundamental_view: Optional[str] = None

    execution_priority: Optional[str] = None