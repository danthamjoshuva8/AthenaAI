from app.models.trade_candidate import TradeCandidate


class TradeAllocatorService:

    def can_allocate(
        self,
        candidate: TradeCandidate,
        available_cash: float,
        max_positions: int,
        current_positions: int
    ) -> tuple[bool, str]:

        # Maximum positions reached
        if current_positions >= max_positions:
            return (
                False,
                "Maximum positions reached"
            )

        capital_required = (
            candidate.entry_price
            *
            candidate.quantity
        )

        # Not enough capital
        if capital_required > available_cash:
            return (
                False,
                "Insufficient capital"
            )

        return (
            True,
            "Eligible"
        )