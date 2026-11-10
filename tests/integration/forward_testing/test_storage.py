from datetime import date

from app.forward_testing.forward_testing_storage_service import ForwardTestingStorageService
from app.forward_testing.storage import PaperOrder, PaperPosition, PaperPositionEvent


def sample_execution():
    return {
        "orders": [{
            "symbol": "RELIANCE",
            "status": "EXECUTED",
            "order_type": "BUY",
            "execution_date": "2026-11-11",
            "quantity": 10,
            "signal_entry_price": 100.0,
            "execution_price": 100.05,
            "stop_loss": 95.0,
            "gross_value": 1000.5,
            "brokerage": 0.0,
            "total_cost": 1000.5,
            "slippage_bps": 5,
            "risk_amount": 50.5,
        }, {
            "symbol": "TCS",
            "status": "REJECTED",
            "execution_date": "2026-11-11",
            "reason": "Invalid quantity",
        }],
    }


def sample_initialization():
    return {
        "positions": [{
            "symbol": "RELIANCE",
            "entry_date": "2026-11-11",
            "entry_price": 100.05,
            "quantity": 10,
            "remaining_quantity": 10,
            "stop_loss": 95.0,
            "initial_stop_loss": 95.0,
            "initial_risk": 5.05,
            "target_2r": 110.15,
            "target_3r": 115.2,
            "partial_exit_2r": False,
            "partial_exit_3r": False,
            "trail_active": False,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "status": "OPEN",
            "exit_strategy": "PARTIAL_2R_3R",
        }],
    }


def test_saves_executed_and_rejected_orders_and_position(db):
    service = ForwardTestingStorageService()
    run = service.start_daily_run(
        db=db,
        signal_date=date(2026, 11, 20),
        execution_date=date(2026, 11, 21),
    )

    result = service.save_execution_and_positions(
        db=db,
        execution_result=sample_execution(),
        initialization_result=sample_initialization(),
        run_id=run["run_id"],
    )
    assert result["status"] == "SUCCESS"
    assert result["orders_saved"] == 2
    assert result["positions_saved"] == 1
    assert db.query(PaperOrder).count() == 2
    assert db.query(PaperPosition).count() == 1
    position = db.query(PaperPosition).one()
    assert position.order_id is not None
    assert position.symbol == "RELIANCE"


def test_get_open_positions_returns_storage_id(db):
    service = ForwardTestingStorageService()
    run = service.start_daily_run(
        db=db,
        signal_date=date(2026, 11, 20),
        execution_date=date(2026, 11, 21),
    )

    service.save_execution_and_positions(
        db,
        sample_execution(),
        sample_initialization(),
        run_id=run["run_id"],
    )
    positions = service.get_open_positions(db)
    assert len(positions) == 1
    assert positions[0]["_storage_id"] is not None
    assert positions[0]["symbol"] == "RELIANCE"


def test_updates_position_and_persists_exit_event(db):
    service = ForwardTestingStorageService()
    run = service.start_daily_run(
        db=db,
        signal_date=date(2026, 11, 20),
        execution_date=date(2026, 11, 21),
    )

    service.save_execution_and_positions(
        db,
        sample_execution(),
        sample_initialization(),
        run_id=run["run_id"],
    )
    position = service.get_open_positions(db)[0]
    position.update({
        "remaining_quantity": 5,
        "realized_pnl": 25.0,
        "unrealized_pnl": 10.0,
        "status": "OPEN",
        "last_updated_date": "2026-11-12",
    })
    result = service.update_position_results(
        db,
        {
            "open_positions": [position],
            "closed_positions": [],
            "exit_events": [{
                "symbol": "RELIANCE",
                "exit_date": "2026-11-12",
                "action": "PARTIAL_CLOSE",
                "sell_quantity": 5,
                "remaining_quantity": 5,
                "exit_price": 105.0,
                "exit_reason": "TARGET_2R",
                "realized_pnl": 25.0,
                "cumulative_realized_pnl": 25.0,
            }],
        },
    )
    assert result["positions_updated"] == 1
    assert result["exit_events_saved"] == 1
    stored = db.query(PaperPosition).one()
    assert stored.remaining_quantity == 5
    assert stored.realized_pnl == 25.0
    event = db.query(PaperPositionEvent).one()
    assert event.exit_reason == "TARGET_2R"
