"""
Technical AI Models

Data models used by the Technical Intelligence Agent.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TechnicalAnalysis:

    trade_score: float = 0.0

    technical_confidence: float = 0.0

    trend_strength: float = 0.0

    breakout_strength: float = 0.0

    volume_strength: float = 0.0

    quality_score: float = 0.0

    reasons: list[str] = field(default_factory=list)

    metadata: Dict[str, float] = field(default_factory=dict)

    def add_reason(self, reason: str) -> None:
        self.reasons.append(reason)

    def add_metadata(self, key: str, value: float) -> None:
        self.metadata[key] = value