from datetime import date

from app.forward_testing.paper_execution_engine import PaperExecutionEngine


EXECUTION_DATE = date(2026, 11, 11)


def approved(**overrides):
    data = {
        "symbol": "RELIANCE",
        "quantity": 100,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "position_value": 20_000.0,
    }
    data.update(overrides)
    return data


def candle(**overrides):
    data = {"open": 100.0, "high": 103.0, "low": 99.0, "close": 102.0}
    data.update(overrides)
    return data


def test_buy_executes_at_open_plus_slippage():
    engine = PaperExecutionEngine(slippage_bps=5, brokerage_pct=0.0)
    result = engine.execute_order(approved(), candle(), EXECUTION_DATE)

    assert result["status"] == "EXECUTED"
    assert result["order_type"] == "BUY"
    assert result["execution_price"] == 100.05
    assert result["gross_value"] == 10_005.0
    assert result["total_cost"] == 10_005.0


def test_missing_market_data_returns_pending():
    engine = PaperExecutionEngine()
    result = engine.execute_order(approved(), None, EXECUTION_DATE)
    assert result["status"] == "PENDING"


def test_allocation_overrun_is_rejected():
    engine = PaperExecutionEngine(slippage_bps=5, brokerage_pct=0.0)
    result = engine.execute_order(
        approved(position_value=9_000),
        candle(open=100),
        EXECUTION_DATE,
    )
    assert result["status"] == "REJECTED"
    assert "exceeds approved allocation" in result["reason"]


def test_invalid_quantity_is_rejected():
    engine = PaperExecutionEngine()
    result = engine.execute_order(approved(quantity=0), candle(), EXECUTION_DATE)
    assert result["status"] == "REJECTED"
    assert "quantity" in result["reason"].lower()


def test_execute_orders_counts_executed_pending_and_rejected():
    engine = PaperExecutionEngine(slippage_bps=5)
    result = engine.execute_orders(
        approved_positions=[
            approved(),
            approved(symbol="TCS"),
            approved(symbol="INFY", quantity=0),
        ],
        market_data_by_symbol={
            "RELIANCE": candle(),
            "INFY": candle(),
        },
        execution_date=EXECUTION_DATE,
    )
    assert result["total_orders"] == 3
    assert result["executed_count"] == 1
    assert result["pending_count"] == 1
    assert result["rejected_count"] == 1
