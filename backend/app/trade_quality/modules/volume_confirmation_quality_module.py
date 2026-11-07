from app.trade_quality.base_quality_module import BaseTradeQualityModule


class VolumeConfirmationQualityModule(BaseTradeQualityModule):
    """
    Evaluates trade candidates based on volume confirmation,
    breakout candle strength, and trading participation.

    Awards points when volume confirmation is present, with
    additional points for a strong candle body and high volume ratio.
    """

    @property
    def module_name(self):
        """Return the identifier of this trade quality module."""
        return "volume_confirmation"

    def calculate_score(self, candidate):
        """
        Calculate the volume confirmation score for a trade candidate.

        Args:
            candidate: Trade candidate containing volume confirmation,
                candle body percentage, and volume ratio.

        Returns:
            A score between 0 and 15 based on volume confirmation
            and breakout strength.
        """

        # Reject candidates without volume confirmation.
        if not candidate.volume_confirmation:
            return 0

        # Award base points for confirmed volume.
        score = 5

        # Reward a strong breakout candle with a large body.
        if candidate.body_percent >= 70:
            score += 5

        # Reward strong market participation relative to average volume.
        if candidate.volume_ratio >= 2:
            score += 5

        # Keep the maximum score capped at 15.
        return min(score, 15)