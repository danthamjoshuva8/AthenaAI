
from app.trade_quality.base_quality_module import BaseTradeQualityModule


class DistanceQualityModule(BaseTradeQualityModule):
    """
    Evaluates trade candidates based on their distance from the short
    moving average.

    Assigns a quality score according to the percentage distance
    between the entry price and the moving average.
    """

    @property
    def module_name(self):
        """Return the identifier of this trade quality module."""
        return "distance_ma"

    def calculate_score(self, candidate):
        """
        Calculate the distance-based quality score.

        Args:
            candidate: Trade candidate containing the distance from
                the moving average.

        Returns:
            Score based on the candidate's distance from the moving average.
        """

        # Retrieve the percentage distance from the moving average.
        d = candidate.distance_from_ma

        # Assign a score based on the distance percentage.
        if d >= 7:
            return 30
        elif d >= 5:
            return 27
        elif d >= 4:
            return 24
        elif d >= 3:
            return 20
        elif d >= 2:
            return 14
        elif d >= 1:
            return 8
        else:
            return 3
