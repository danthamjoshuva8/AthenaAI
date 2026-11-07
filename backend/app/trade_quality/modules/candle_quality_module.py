
from app.models.trade_candidate import TradeCandidate
from app.trade_quality.base_quality_module import BaseTradeQualityModule


class CandleQualityModule(BaseTradeQualityModule):
    """
    Evaluates trade candidates based on candle body size and quality.

    Assigns a score according to the candle body percentage and
    provides an additional score when the candle passes the
    configured candle quality conditions.
    """

    @property
    def module_name(self):
        """Return the identifier of this trade quality module."""
        return "candle"

    def calculate_score(
        self,
        candidate: TradeCandidate
    ):
        """
        Calculate the candle quality score for a trade candidate.

        Scores the candle based on its body percentage and adds a
        bonus when the candidate passes the candle quality checks.

        Args:
            candidate: Trade candidate containing candle metrics
                and quality evaluation results.

        Returns:
            Candle quality score, capped at 10.
        """

        # Retrieve the candle body percentage.
        body = candidate.body_percent

        # Assign the base score based on candle body size.
        if body >= 4:
            score = 10
        elif body >= 3:
            score = 8
        elif body >= 2:
            score = 6
        else:
            score = 3

        # Add a quality bonus when all candle quality conditions pass.
        if candidate.quality_pass:
            score = min(score + 2, 10)

        return score
