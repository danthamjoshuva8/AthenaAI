from dataclasses import dataclass, field
from typing import List


@dataclass
class NewsAnalysis:

    symbol: str

    news_score: float = 50.0

    sentiment_score: float = 50.0

    confidence: float = 50.0

    headlines: List[str] = field(default_factory=list)

    positive_count: int = 0

    negative_count: int = 0

    neutral_count: int = 0

    summary: str = ""

    def final_score(self):

        return round(
            (
                self.news_score +
                self.sentiment_score +
                self.confidence
            ) / 3,
            2
        )