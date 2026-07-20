from app.models.trade_candidate import TradeCandidate


class PositionSizingService:

    def calculate_position_size(
        self,
        candidate: TradeCandidate,
        portfolio_value: float,
        risk_percent: float = 1.0
    ) -> TradeCandidate:

        # Risk amount
        risk_amount = (
            portfolio_value
            * risk_percent
            / 100
        )

        # Risk per share
        risk_per_share = (
            candidate.entry_price
            - candidate.stop_loss
        )

        if risk_per_share <= 0:

            candidate.quantity = 0

            candidate.capital_required = 0

            return candidate

        quantity = int(

            risk_amount
            / risk_per_share

        )

        candidate.quantity = quantity

        candidate.capital_required = round(

            quantity
            * candidate.entry_price,

            2

        )

        candidate.risk_amount = risk_amount

        return candidate