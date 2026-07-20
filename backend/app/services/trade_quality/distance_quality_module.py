from app.models.trade_candidate import TradeCandidate
from app.services.trade_quality.base_quality_module import BaseTradeQualityModule


class DistanceQualityModule(BaseTradeQualityModule):

    @property
    def module_name(self):
        return "distance_ma"

    def calculate_score(self, candidate):

        d = candidate.distance_from_ma

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