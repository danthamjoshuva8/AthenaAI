from app.trade_quality.base_quality_module import BaseTradeQualityModule


class SectorQualityModule(BaseTradeQualityModule):
    """
    Evaluates trade candidates based on their sector quality score.

    Uses the sector score already calculated for the candidate as
    this module's contribution to the overall trade quality score.
    """

    @property
    def module_name(self):
        """Return the identifier of this trade quality module."""
        return "sector"

    def calculate_score(self, candidate):
        """
        Retrieve the sector quality score for a trade candidate.

        Args:
            candidate: Trade candidate containing the calculated sector score.

        Returns:
            The sector quality score assigned to the candidate.
        """

        # Use the sector score calculated during candidate evaluation.
        return candidate.sector_score