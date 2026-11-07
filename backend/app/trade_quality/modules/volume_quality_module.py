from app.models.trade_candidate import TradeCandidate
from app.trade_quality.base_quality_module import BaseTradeQualityModule


class VolumeQualityModule(BaseTradeQualityModule):
    """
    Evaluates trade candidates based on their volume ratio.

    Assigns higher scores to candidates with stronger trading volume
    relative to the average volume.
    """

    @property
    def module_name(self) -> str:
        """Return the identifier of this trade quality module."""
        return "volume"

    def calculate_score(
        self,
        candidate: TradeCandidate
    ) -> float:
        """
        Calculate the volume quality score using the candidate's volume ratio.

        Args:
            candidate: Trade candidate containing the calculated volume ratio.

        Returns:
            A volume quality score between 5 and 25.
        """

        # Retrieve the candidate's volume relative to average volume.
        vr = candidate.volume_ratio

        # Assign scores based on the strength of volume participation.
        if vr >= 4:
            return 25
        elif vr >= 3:
            return 22
        elif vr >= 2:
            return 18
        elif vr >= 1.5:
            return 14
        elif vr >= 1:
            return 10
        else:
            return 5