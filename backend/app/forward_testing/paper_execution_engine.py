
from datetime import date
from typing import Any


class PaperExecutionEngine:
    """
    Simulates paper BUY order execution using next-session OHLC data.

    Execution rule:
        - BUY orders execute at the next session's OPEN.
        - Slippage is applied to the opening price.
        - Orders exceeding their approved allocation are rejected.
        - No live broker orders are submitted.
    """

    def __init__(
        self,
        slippage_bps: float = 5.0,
        brokerage_pct: float = 0.0,
    ):
        if slippage_bps < 0:
            raise ValueError("Slippage cannot be negative.")

        if brokerage_pct < 0:
            raise ValueError("Brokerage percentage cannot be negative.")

        self.slippage_bps = slippage_bps
        self.brokerage_pct = brokerage_pct

    def _calculate_execution_price(
        self,
        opening_price: float,
    ) -> float:
        """Apply BUY-side slippage to the opening price."""

        slippage = self.slippage_bps / 10_000

        return round(
            opening_price * (1 + slippage),
            2,
        )

    def _reject(
        self,
        symbol: str,
        reason: str,
        execution_date: date,
    ) -> dict[str, Any]:

        return {
            "symbol": symbol,
            "status": "REJECTED",
            "execution_date": execution_date.isoformat(),
            "reason": reason,
        }

    def execute_order(
        self,
        approved_position: dict[str, Any],
        market_data: dict[str, Any] | None,
        execution_date: date,
    ) -> dict[str, Any]:
        """
        Execute one approved paper BUY order.

        Expected approved_position fields:
            symbol
            quantity
            entry_price
            stop_loss
            position_value

        Expected market_data fields:
            open, high, low, close

        The market_data must belong to execution_date.
        """

        symbol = str(
            approved_position.get("symbol", "")
        ).upper()

        if not symbol:
            return self._reject(
                symbol="UNKNOWN",
                reason="Missing symbol",
                execution_date=execution_date,
            )

        if market_data is None:
            return {
                "symbol": symbol,
                "status": "PENDING",
                "execution_date": execution_date.isoformat(),
                "reason": "Next-session market data unavailable",
            }

        try:
            quantity = int(approved_position["quantity"])
            approved_allocation = float(
                approved_position["position_value"]
            )
            entry_price = float(
                approved_position["entry_price"]
            )
            stop_loss = float(
                approved_position["stop_loss"]
            )
            opening_price = float(market_data["open"])

        except (KeyError, TypeError, ValueError):
            return self._reject(
                symbol,
                "Missing or invalid order/market data fields",
                execution_date,
            )

        if quantity <= 0:
            return self._reject(
                symbol,
                "Invalid order quantity",
                execution_date,
            )

        if (
            entry_price <= 0
            or stop_loss <= 0
            or opening_price <= 0
            or approved_allocation <= 0
        ):
            return self._reject(
                symbol,
                "Prices and approved allocation must be positive",
                execution_date,
            )

        if stop_loss >= entry_price:
            return self._reject(
                symbol,
                "Stop loss must be below entry price",
                execution_date,
            )

        # Execute using the next session's opening price.
        execution_price = self._calculate_execution_price(
            opening_price
        )

        gross_value = round(
            execution_price * quantity,
            2,
        )

        brokerage = round(
            gross_value * self.brokerage_pct / 100,
            2,
        )

        total_cost = round(
            gross_value + brokerage,
            2,
        )

        # Do not exceed the allocation approved by the portfolio manager.
        if total_cost > approved_allocation:
            return self._reject(
                symbol,
                (
                    f"Execution cost {total_cost} exceeds "
                    f"approved allocation {approved_allocation}"
                ),
                execution_date,
            )

        actual_risk = round(
            (execution_price - stop_loss) * quantity,
            2,
        )

        return {
            "symbol": symbol,
            "status": "EXECUTED",
            "order_type": "BUY",
            "execution_date": execution_date.isoformat(),
            "quantity": quantity,
            "signal_entry_price": entry_price,
            "execution_price": execution_price,
            "stop_loss": stop_loss,
            "gross_value": gross_value,
            "brokerage": brokerage,
            "total_cost": total_cost,
            "slippage_bps": self.slippage_bps,
            "risk_amount": actual_risk,
            "market_open": opening_price,
        }

    def execute_orders(
        self,
        approved_positions: list[dict[str, Any]],
        market_data_by_symbol: dict[str, dict[str, Any]],
        execution_date: date,
    ) -> dict[str, Any]:
        """
        Execute all portfolio-approved paper BUY orders.

        market_data_by_symbol example:
        {
            "RELIANCE": {
                "open": 1450.0,
                "high": 1470.0,
                "low": 1440.0,
                "close": 1460.0
            }
        }
        """

        results = []

        for position in approved_positions:
            symbol = str(
                position.get("symbol", "")
            ).upper()

            market_data = market_data_by_symbol.get(symbol)

            result = self.execute_order(
                approved_position=position,
                market_data=market_data,
                execution_date=execution_date,
            )

            results.append(result)

        executed = [
            order for order in results
            if order["status"] == "EXECUTED"
        ]

        pending = [
            order for order in results
            if order["status"] == "PENDING"
        ]

        rejected = [
            order for order in results
            if order["status"] == "REJECTED"
        ]

        return {
            "status": "SUCCESS",
            "execution_date": execution_date.isoformat(),
            "total_orders": len(results),
            "executed_count": len(executed),
            "pending_count": len(pending),
            "rejected_count": len(rejected),
            "total_execution_value": round(
                sum(order["total_cost"] for order in executed),
                2,
            ),
            "orders": results,
        }
