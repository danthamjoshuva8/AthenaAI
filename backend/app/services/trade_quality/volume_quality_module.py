from app.models.trade_candidate import TradeCandidate
from app.services.trade_quality.base_quality_module import BaseTradeQualityModule


class VolumeQualityModule(BaseTradeQualityModule):

    @property
    def module_name(self) -> str:
        return "volume"

    def calculate_score(
        self,
        candidate: TradeCandidate
    ) -> float:

        vr = candidate.volume_ratio

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