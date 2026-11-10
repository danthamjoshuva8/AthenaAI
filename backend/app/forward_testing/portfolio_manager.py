
import math
from typing import Any

from app.forward_testing.config.portfolio_config import (
    FORWARD_TESTING_PORTFOLIO_CONFIG,
)


class ForwardTestingPortfolioManager:
    """
    Manages capital allocation and position eligibility
    for AthenaAI forward testing.

    Candidates must already be ranked by the existing
    AthenaAI ranking engine.
    """

    def __init__(self):
        self.config = FORWARD_TESTING_PORTFOLIO_CONFIG

        self.capital = self.config.initial_capital
        self.max_positions = self.config.max_positions
        self.risk_per_trade = self.config.risk_per_trade_pct

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        available_capital: float,
        remaining_portfolio_risk: float,
    ) -> dict[str, Any]:
        """
        Calculate position quantity using risk and allocation limits.
        """

        if entry_price <= 0 or stop_loss <= 0:
            return {"eligible": False, "reason": "Invalid entry or stop price"}

        if stop_loss >= entry_price:
            return {"eligible": False, "reason": "Stop loss must be below entry price"}

        risk_per_share = entry_price - stop_loss

        risk_budget = min(
            self.capital * self.risk_per_trade / 100,
            remaining_portfolio_risk,
        )

        max_position_value = (
            self.capital
            * self.config.max_position_allocation_pct
            / 100
        )

        quantity_by_risk = math.floor(risk_budget / risk_per_share)
        quantity_by_allocation = math.floor(
            max_position_value / entry_price
        )
        quantity_by_capital = math.floor(
            available_capital / entry_price
        )

        quantity = min(
            quantity_by_risk,
            quantity_by_allocation,
            quantity_by_capital,
        )

        if quantity <= 0:
            return {
                "eligible": False,
                "reason": "Insufficient capital or risk budget",
            }

        position_value = quantity * entry_price
        actual_risk = quantity * risk_per_share

        return {
            "eligible": True,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "position_value": round(position_value, 2),
            "risk_amount": round(actual_risk, 2),
            "risk_percentage": round(
                actual_risk / self.capital * 100, 2
            ),
        }

    def evaluate_candidates(
        self,
        candidates: list[dict[str, Any]],
        current_positions: list[dict[str, Any]] | None = None,
        available_capital: float | None = None,
        entries_today: int = 0,
    ) -> dict[str, Any]:
        """
        Evaluate ranked BUY candidates against portfolio constraints.

        Expected candidate fields:
            symbol, entry_price, stop_loss

        Expected open-position fields:
            symbol, quantity, entry_price, stop_loss

        Candidate order is preserved. The ranking engine is
        responsible for ranking candidates before this method.
        """

        if not self.config.enable_paper_trading:
            return {
                "status": "DISABLED",
                "accepted": [],
                "rejected": [],
                "reason": "Paper trading is disabled",
            }

        if not self.config.allow_new_positions:
            return {
                "status": "DISABLED",
                "accepted": [],
                "rejected": [],
                "reason": "New positions are disabled",
            }

        current_positions = current_positions or []

        available_capital = (
            self.capital
            if available_capital is None
            else available_capital
        )

        if available_capital < 0:
            raise ValueError("Available capital cannot be negative.")

        if entries_today < 0:
            raise ValueError("Entries today cannot be negative.")

        accepted = []
        rejected = []

        open_position_count = len(current_positions)

        invested_value = sum(
            float(position.get("quantity", 0))
            * float(position.get("entry_price", 0))
            for position in current_positions
        )

        existing_risk = sum(
            max(
                0.0,
                float(position.get("quantity", 0))
                * (
                    float(position.get("entry_price", 0))
                    - float(position.get("stop_loss", 0))
                ),
            )
            for position in current_positions
        )

        max_allocation = (
            self.capital
            * self.config.max_portfolio_allocation_pct
            / 100
        )

        remaining_allocation = max(0.0, max_allocation - invested_value)

        max_portfolio_risk = (
            self.capital
            * self.config.max_portfolio_risk_pct
            / 100
        )

        remaining_risk = max(0.0, max_portfolio_risk - existing_risk)

        existing_symbols = {
            str(position["symbol"]).upper()
            for position in current_positions
            if position.get("symbol")
        }

        seen_symbols = set(existing_symbols)

        daily_entries_remaining = max(
            0,
            self.config.max_new_positions_per_day - entries_today,
        )

        for candidate in candidates:

            symbol = str(candidate.get("symbol", "")).upper()

            if not symbol:
                rejected.append({
                    "candidate": candidate,
                    "reason": "Missing symbol",
                })
                continue

            if not self.config.allow_multiple_positions_per_symbol:
                if symbol in seen_symbols:
                    rejected.append({
                        "symbol": symbol,
                        "reason": "Position already exists or candidate duplicated",
                    })
                    continue

            if open_position_count + len(accepted) >= self.max_positions:
                rejected.append({
                    "symbol": symbol,
                    "reason": "Maximum open positions reached",
                })
                continue

            if len(accepted) >= daily_entries_remaining:
                rejected.append({
                    "symbol": symbol,
                    "reason": "Daily new-position limit reached",
                })
                continue

            entry_price = candidate.get("entry_price")
            stop_loss = candidate.get("stop_loss")

            if entry_price is None or stop_loss is None:
                rejected.append({
                    "symbol": symbol,
                    "reason": "Missing entry price or stop loss",
                })
                continue

            sizing = self.calculate_position_size(
                entry_price=float(entry_price),
                stop_loss=float(stop_loss),
                available_capital=min(
                    available_capital,
                    remaining_allocation,
                ),
                remaining_portfolio_risk=remaining_risk,
            )

            if not sizing["eligible"]:
                rejected.append({
                    "symbol": symbol,
                    "reason": sizing["reason"],
                })
                continue

            position = {
                **candidate,
                **sizing,
                "symbol": symbol,
            }

            accepted.append(position)

            available_capital -= sizing["position_value"]
            remaining_allocation -= sizing["position_value"]
            remaining_risk -= sizing["risk_amount"]

            seen_symbols.add(symbol)

        return {
            "status": "SUCCESS",
            "initial_capital": self.capital,
            "available_capital": round(available_capital, 2),
            "existing_positions": open_position_count,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "accepted": accepted,
            "rejected": rejected,
        }
