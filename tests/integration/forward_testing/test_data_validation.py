from datetime import date

from app.forward_testing.paper_execution_engine import PaperExecutionEngine
from app.forward_testing.position_manager import ForwardTestingPositionManager
from app.config.backtest_config import ExitStrategyType


def test_order_rejects_missing_required_fields():
    engine = PaperExecutionEngine()
    result = engine.execute_order(
        {"symbol": "RELIANCE", "quantity": 10},
        {"open": 100},
        date(2026, 11, 11),
    )
    assert result["status"] == "REJECTED"


def test_position_manager_skips_missing_ohlc_fields():
    manager = ForwardTestingPositionManager(ExitStrategyType.PARTIAL_2R_3R)
    position = {
        "symbol": "RELIANCE",
        "entry_date": "2026-11-11",
        "entry_price": 100.0,
        "quantity": 10,
        "remaining_quantity": 10,
        "stop_loss": 95.0,
        "initial_stop_loss": 95.0,
        "initial_risk": 5.0,
        "target_2r": 110.0,
        "target_3r": 115.0,
        "partial_exit_2r": False,
        "partial_exit_3r": False,
        "trail_active": False,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "status": "OPEN",
        "exit_strategy": "PARTIAL_2R_3R",
    }
    result = manager.process_positions(
        [position],
        {"RELIANCE": {"open": 100, "high": 101, "close": 100}},
        date(2026, 11, 12),
    )
    assert len(result["skipped_positions"]) == 1
    assert result["open_positions"][0]["remaining_quantity"] == 10


def test_position_manager_skips_invalid_ohlc_values():
    manager = ForwardTestingPositionManager(ExitStrategyType.PARTIAL_2R_3R)
    position = {
        "symbol": "RELIANCE", "entry_date": "2026-11-11",
        "entry_price": 100.0, "quantity": 10, "remaining_quantity": 10,
        "stop_loss": 95.0, "initial_stop_loss": 95.0, "initial_risk": 5.0,
        "target_2r": 110.0, "target_3r": 115.0,
        "partial_exit_2r": False, "partial_exit_3r": False,
        "trail_active": False, "realized_pnl": 0.0, "unrealized_pnl": 0.0,
        "status": "OPEN", "exit_strategy": "PARTIAL_2R_3R",
    }
    result = manager.process_positions(
        [position],
        {"RELIANCE": {"open": 100, "high": 90, "low": 95, "close": 98}},
        date(2026, 11, 12),
    )
    assert len(result["skipped_positions"]) == 1
