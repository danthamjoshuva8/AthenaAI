from app.models.trade_candidate import TradeCandidate
from app.config.trade_quality_config import (
    TradeQualityConfig
)
from app.models.trade_quality_score import TradeQualityScore
from app.services.trade_quality.volume_quality_module import VolumeQualityModule
from app.services.trade_quality.distance_quality_module import DistanceQualityModule


class TradeRankingService:

    def __init__(self):

        self.config = TradeQualityConfig()
        self.volume_module = VolumeQualityModule()
        self.distance_module = DistanceQualityModule()

    def rank_candidates(
        self,
        candidates
    ):

        for candidate in candidates:

            quality_score = TradeQualityScore()

            if self.config.volume.enabled:

                volume_score = min(
                    self.volume_module.calculate_score(candidate),
                    self.config.volume.weight
                )

                quality_score.add_score(
                    self.volume_module.module_name,
                    volume_score
                )

            if self.config.distance_from_ma.enabled:

                distance_score = min(
                    self.distance_module.calculate_score(candidate),
                    self.config.distance_from_ma.weight
                )

                quality_score.add_score(
                    self.distance_module.module_name,
                    distance_score
                )

            # Volume Confirmation
            if (
                self.config.volume_confirmation.enabled
                and candidate.volume_confirmation
            ):
                quality_score.add_score(
                    "volume_confirmation",
                    self.config.volume_confirmation.weight
                )

            if self.config.candle_quality.enabled:

                if candidate.body_percent >= 4:
                    candle_score = 10
                elif candidate.body_percent >= 3:
                    candle_score = 8
                elif candidate.body_percent >= 2:
                    candle_score = 6
                else:
                    candle_score = 3

                if candidate.quality_pass:
                    candle_score = min(
                        candle_score + 2,
                        self.config.candle_quality.weight
                    )

                quality_score.add_score(
                    "candle",
                    candle_score
                )

            if self.config.market.enabled:

                quality_score.add_score(
                    "market",
                    min(
                        candidate.market_score,
                        self.config.market.weight
                    )
                )

            if self.config.sector.enabled:

                quality_score.add_score(
                    "sector",
                    min(
                        candidate.sector_score,
                        self.config.sector.weight
                    )
                )

            candidate.trade_quality = quality_score
            candidate.total_score = round(quality_score.total_score, 2)

        candidates.sort(
            key=lambda x: x.total_score,
            reverse=True
        )

        return candidates