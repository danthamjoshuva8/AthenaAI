from app.models.trade_candidate import TradeCandidate


class PositionSizer:
    """
    Calculates the number of shares to purchase based on portfolio value,
    risk percentage, entry price, and stop-loss price.

    Updates the trade candidate with the calculated quantity,
    required capital, and risk amount.
    """

    def calculate_position_size(
        self,
        candidate: TradeCandidate,
        portfolio_value: float,
        risk_percent: float = 1.0
    ) -> TradeCandidate:
        """
        Calculate the position size for a trade candidate.

        Determines the maximum risk amount based on the portfolio value
        and risk percentage, then calculates the quantity using the
        risk per share.

        Args:
            candidate: Trade candidate containing entry and stop-loss prices.
            portfolio_value: Total portfolio value used for risk calculation.
            risk_percent: Percentage of portfolio value allocated as trade
                risk. Defaults to 1.0%.

        Returns:
            The updated trade candidate containing quantity,
            capital required, and risk amount.
        """

        # Calculate the maximum monetary risk allowed for the trade.
        risk_amount = (
            portfolio_value
            * risk_percent
            / 100
        )

        # Calculate the potential loss per share based on entry and stop-loss.
        risk_per_share = (
            candidate.entry_price
            - candidate.stop_loss
        )

        # Prevent position sizing when the stop-loss is not below entry price.
        if risk_per_share <= 0:

            candidate.quantity = 0

            candidate.capital_required = 0

            return candidate

        # Calculate the maximum whole-share quantity within the risk limit.
        quantity = int(

            risk_amount
            / risk_per_share

        )

        # Store the calculated position quantity.
        candidate.quantity = quantity

        # Calculate the total capital required to purchase the position.
        candidate.capital_required = round(

            quantity
            * candidate.entry_price,

            2

        )

        # Store the monetary risk allocated to this trade.
        candidate.risk_amount = risk_amount

        # Return the candidate with its updated position sizing details.
        return candidate