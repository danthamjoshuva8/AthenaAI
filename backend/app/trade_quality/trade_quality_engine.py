from app.config.trade_quality_config import TradeQualityConfig
from app.models.trade_quality_score import TradeQualityScore
from app.trade_quality.modules.distance_quality_module import DistanceQualityModule
from app.trade_quality.modules.market_quality_module import MarketQualityModule
from app.trade_quality.modules.volume_quality_module import VolumeQualityModule
from app.trade_quality.modules.candle_quality_module import CandleQualityModule
from app.trade_quality.modules.sector_quality_module import SectorQualityModule
from app.trade_quality.modules.volume_confirmation_quality_module import VolumeConfirmationQualityModule


class TradeQualityEngine:
    """
    Coordinates the trade quality modules to calculate an overall
    quality score for a trade candidate.

    Each module evaluates a specific aspect of the candidate.
    Its score is capped by the corresponding configured weight
    before being added to the final trade quality score.
    """

    def __init__(self):
        """
        Initialize the trade quality configuration and scoring modules.

        Creates one instance of each quality module used by the engine.
        """

        # Load configuration containing module enablement and score weights.
        self.config = TradeQualityConfig()

        # Initialize individual trade quality scoring modules.
        self.volume_module = VolumeQualityModule()

        self.distance_module = DistanceQualityModule()

        self.market_module = MarketQualityModule()

        self.volume_confirmation_module = VolumeConfirmationQualityModule()

        self.candle_module = CandleQualityModule()

        self.sector_module = SectorQualityModule()

    def calculate(
        self,
        candidate
    ):
        """
        Calculate the overall trade quality score for a candidate.

        Evaluates each enabled quality module, limits its contribution
        to the configured weight, and adds the result to the combined
        trade quality score.

        Updates the candidate with its trade quality breakdown and
        rounded total score.

        Args:
            candidate: Trade candidate containing the inputs required
                by the enabled quality modules.

        Returns:
            The updated trade candidate with its calculated trade
            quality score and total score.
        """

        # Create an object to collect individual module scores.
        quality_score = TradeQualityScore()

        # Evaluate volume quality when the module is enabled.
        if self.config.volume.enabled:

            # Cap the module score at its configured maximum weight.
            score = min(
                self.volume_module.calculate_score(candidate),
                self.config.volume.weight
            )

            quality_score.add_score(
                self.volume_module.module_name,
                score
            )

        # Evaluate volume confirmation when the module is enabled.
        if self.config.volume_confirmation.enabled:

            # Cap the module score at its configured maximum weight.
            score = min(
                self.volume_confirmation_module.calculate_score(candidate),
                self.config.volume_confirmation.weight
            )

            quality_score.add_score(
                self.volume_confirmation_module.module_name,
                score
            )

        # Evaluate distance from the moving average when enabled.
        if self.config.distance_from_ma.enabled:

            # Cap the module score at its configured maximum weight.
            score = min(
                self.distance_module.calculate_score(candidate),
                self.config.distance_from_ma.weight
            )

            quality_score.add_score(
                self.distance_module.module_name,
                score
            )

        # Evaluate candle quality when the module is enabled.
        if self.config.candle_quality.enabled:

            # Cap the module score at its configured maximum weight.
            score = min(
                self.candle_module.calculate_score(candidate),
                self.config.candle_quality.weight
            )

            quality_score.add_score(
                self.candle_module.module_name,
                score
            )

        # Evaluate overall market quality when the module is enabled.
        if self.config.market.enabled:

            # Cap the module score at its configured maximum weight.
            score = min(
                self.market_module.calculate_score(candidate),
                self.config.market.weight
            )

            quality_score.add_score(
                self.market_module.module_name,
                score
            )

        # Evaluate sector quality when the module is enabled.
        if self.config.sector.enabled:

            # Cap the module score at its configured maximum weight.
            score = min(
                self.sector_module.calculate_score(candidate),
                self.config.sector.weight
            )

            quality_score.add_score(
                self.sector_module.module_name,
                score
            )

        # Attach the individual module scores to the candidate.
        candidate.trade_quality = quality_score

        # Store the combined score rounded to two decimal places.
        candidate.total_score = round(
            quality_score.total_score,
            2
        )

        # Return the candidate with its updated quality assessment.
        return candidate