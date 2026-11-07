
from pydantic import BaseModel


class LLMResponse(BaseModel):
    decision: str
    confidence: int

    reasoning: str

    risks: list[str] = []

    strengths: list[str] = []

    weaknesses: list[str] = []

    recommendation: str | None = None

    news_impact: str | None = None

    fundamental_view: str | None = None

    execution_priority: str | None = None