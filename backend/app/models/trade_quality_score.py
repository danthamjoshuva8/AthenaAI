
from dataclasses import dataclass, field


@dataclass
class TradeQualityScore:
    """
    Stores the overall trade quality score and individual module scores.
    """

    total_score: float = 0.0  # Combined score from all evaluation modules.

    module_scores: dict[str, float] = field(default_factory=dict)  # Individual scores assigned by each module.

    def add_score(
        self,
        module: str,
        score: float
    ):
        """
        Adds a module score and updates the overall trade quality score.
        """
        self.module_scores[module] = score
        self.total_score += score

    def get_score(
        self,
        module: str
    ) -> float:
        """
        Returns the score for the specified module.
        Returns 0.0 if the module has no recorded score.
        """
        return self.module_scores.get(module, 0.0)
