
from app.models.market_state import MarketState


class MarketQualityModule:
    """
    Evaluates trade candidates using the overall market quality score.

    Retrieves the market score already calculated for the trade candidate
    and uses it as the market quality module's contribution.
    """

    @property
    def module_name(self):
        """Return the identifier of this trade quality module."""
        return "market"

    def calculate_score(self, candidate):
        """
        Retrieve the market quality score for a trade candidate.

        Args:
            candidate: Trade candidate containing the calculated market score.

        Returns:
            Market score assigned to the candidate.
        """

        # Use the market score calculated during candidate evaluation.
        return candidate.market_score
