from app.models.market_state import MarketState


class MarketQualityModule:

    @property
    def module_name(self):
        return "market"

    def calculate_score(
        self,
        state: MarketState
    ) -> float:

        return state.total_score