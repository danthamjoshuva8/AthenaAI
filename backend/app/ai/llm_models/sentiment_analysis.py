from dataclasses import dataclass, field
from typing import List


@dataclass
class SentimentAnalysis:

    symbol: str

    sentiment_score: float = 50.0

    confidence: float = 50.0

    overall_sentiment: str = "NEUTRAL"

    positive_signals: List[str] = field(default_factory=list)

    negative_signals: List[str] = field(default_factory=list)

    summary: str = ""

    def final_score(self) -> float:
        return round(
            (self.sentiment_score + self.confidence) / 2,
            2
        )