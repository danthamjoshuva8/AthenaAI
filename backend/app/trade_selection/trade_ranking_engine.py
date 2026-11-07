from app.trade_quality.trade_quality_engine import TradeQualityEngine


class TradeRankingEngine:
    """
    Ranks trade candidates based on their overall trade quality scores.

    Uses TradeQualityEngine to calculate each candidate's score
    and sorts the candidates from highest to lowest score.
    """

    def __init__(self):
        """
        Initialize the trade ranking engine.

        Creates the trade quality engine responsible for evaluating
        individual trade candidates.
        """

        # Initialize the engine used to calculate trade quality scores.
        self.trade_quality = TradeQualityEngine()

    def rank_candidates(
        self,
        candidates
    ):
        """
        Calculate quality scores and rank trade candidates.

        Evaluates every candidate using the trade quality engine,
        then sorts the candidates in descending order of total score.

        Args:
            candidates: Collection of trade candidates to evaluate and rank.

        Returns:
            The candidates sorted from highest to lowest total quality score.
        """

        # Calculate the overall trade quality score for each candidate.
        for candidate in candidates:

            self.trade_quality.calculate(candidate)

        # Rank candidates by total score, placing the highest score first.
        candidates.sort(
            key=lambda x: x.total_score,
            reverse=True
        )

        # Return the ranked candidates.
        return candidates