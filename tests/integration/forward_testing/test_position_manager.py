from datetime import date

from app.config.backtest_config import ExitStrategyType
from app.forward_testing.position_manager import ForwardTestingPositionManager


ENTRY_DATE = date(2026, 11, 11)
MARKET_DATE = date(2026, 11, 12)


def manager():
    return ForwardTestingPositionManager(
        exit_strategy=ExitStrategyType.PARTIAL_2R_3R
    )


def execution_result():
    return {
        "orders": [{
            "symbol": "RELIANCE",
            "status": "EXECUTED",
            "quantity": 10,
            "execution_price": 100.0,
            "stop_loss": 95.0,
            "execution_date": ENTRY_DATE.isoformat(),
        }, {
            "symbol": "TCS",
            "status": "REJECTED",
            "reason": "test rejection",
        }],
    }


def test_initializes_only_executed_orders_and_calculates_targets():
    result = manager().initialize_positions(execution_result())
    assert result["initialized_count"] == 1
    position = result["positions"][0]
    assert position["symbol"] == "RELIANCE"
    assert position["remaining_quantity"] == 10
    assert position["initial_risk"] == 5
    assert position["target_2r"] == 110
    assert position["target_3r"] == 115


def test_initial_stop_loss_closes_position():
    position = manager().initialize_positions(execution_result())["positions"][0]
    result = manager().process_positions(
        positions=[position],
        market_data_by_symbol={
            "RELIANCE": {"open": 94, "high": 96, "low": 93, "close": 95}
        },
        market_date=MARKET_DATE,
    )
    closed = result["closed_positions"][0]
    assert closed["status"] == "CLOSED"
    assert closed["remaining_quantity"] == 0
    assert closed["final_exit_reason"] == "STOP_LOSS"
    assert closed["realized_pnl"] == -60.0


def test_partial_exit_at_2r():
    position = manager().initialize_positions(execution_result())["positions"][0]
    result = manager().process_positions(
        positions=[position],
        market_data_by_symbol={
            "RELIANCE": {"open": 100, "high": 111, "low": 99, "close": 108}
        },
        market_date=MARKET_DATE,
    )
    updated = result["open_positions"][0]
    assert updated["partial_exit_2r"] is True
    assert updated["remaining_quantity"] == 5
    assert updated["realized_pnl"] == 50.0
    assert result["exit_events_count"] == 1


def test_remaining_position_exits_at_3r_after_2r_partial():
    position = manager().initialize_positions(execution_result())["positions"][0]
    first = manager().process_positions(
        [position],
        {"RELIANCE": {"open": 100, "high": 111, "low": 99, "close": 108}},
        MARKET_DATE,
    )
    after_2r = first["open_positions"][0]

    second = manager().process_positions(
        [after_2r],
        {"RELIANCE": {"open": 110, "high": 116, "low": 109, "close": 115}},
        date(2026, 11, 13),
    )
    closed = second["closed_positions"][0]
    assert closed["status"] == "CLOSED"
    assert closed["remaining_quantity"] == 0
    assert closed["realized_pnl"] == 125.0


def test_missing_candle_preserves_open_position_and_reports_skip():
    position = manager().initialize_positions(execution_result())["positions"][0]
    result = manager().process_positions(
        [position], {}, MARKET_DATE
    )
    assert result["open_positions"][0]["remaining_quantity"] == 10
    assert result["skipped_positions"][0]["reason"] == "Market data unavailable"


def test_invalid_ohlc_is_skipped_without_mutating_original():
    position = manager().initialize_positions(execution_result())["positions"][0]
    result = manager().process_positions(
        [position],
        {"RELIANCE": {"open": 100, "high": 90, "low": 95, "close": 98}},
        MARKET_DATE,
    )
    assert result["skipped_positions"]
    assert result["open_positions"][0]["remaining_quantity"] == 10
