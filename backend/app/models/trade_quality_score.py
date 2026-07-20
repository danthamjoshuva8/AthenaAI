from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TradeQualityScore:

    total_score: float = 0.0

    module_scores: Dict[str, float] = field(default_factory=dict)

    def add_score(
        self,
        module: str,
        score: float
    ):
        self.module_scores[module] = score
        self.total_score += score

    def get_score(
        self,
        module: str
    ) -> float:
        return self.module_scores.get(module, 0.0)