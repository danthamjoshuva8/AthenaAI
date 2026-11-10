from datetime import date

from app.forward_testing.forward_testing_workflow import ForwardTestingWorkflow
from app.forward_testing.storage import ForwardTestingRun, PaperOrder, PaperPosition


def test_daily_workflow_executes_persists_and_completes_run(db):
    workflow = ForwardTestingWorkflow()
    result = workflow.execute_daily_orders(
        db=db,
        ranked_candidates=[{
            "symbol": "RELIANCE",
            "entry_price": 100.0,
            "stop_loss": 95.0,
        }],
        available_capital=100_000.0,
        entries_today=0,
        next_session_market_data={
            "RELIANCE": {
                "open": 99.0, "high": 101.0,
                "low": 98.0, "close": 100.0,
            }
        },
        signal_date=date(2026, 11, 10),
        execution_date=date(2026, 11, 11),
    )
    assert result["status"] == "SUCCESS"
    assert result["execution"]["executed_count"] == 1
    assert result["storage"]["orders_saved"] == 1
    assert result["storage"]["positions_saved"] == 1
    assert db.query(PaperOrder).count() == 1
    assert db.query(PaperPosition).count() == 1

    run = db.query(ForwardTestingRun).one()
    assert run.status == "SUCCESS"


def test_workflow_skips_duplicate_successful_run(db):
    workflow = ForwardTestingWorkflow()
    kwargs = dict(
        db=db,
        ranked_candidates=[],
        available_capital=100_000.0,
        entries_today=0,
        next_session_market_data={},
        signal_date=date(2026, 11, 10),
        execution_date=date(2026, 11, 11),
    )
    first = workflow.execute_daily_orders(**kwargs)
    second = workflow.execute_daily_orders(**kwargs)
    assert first["status"] == "SUCCESS"
    assert second["status"] == "SKIPPED"
    assert db.query(ForwardTestingRun).count() == 1


def test_monitor_positions_updates_open_position(db):
    workflow = ForwardTestingWorkflow()
    workflow.execute_daily_orders(
        db=db,
        ranked_candidates=[{
            "symbol": "RELIANCE", "entry_price": 100.0, "stop_loss": 95.0
        }],
        available_capital=100_000.0,
        entries_today=0,
        next_session_market_data={
            "RELIANCE": {"open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0}
        },
        signal_date=date(2026, 11, 10),
        execution_date=date(2026, 11, 11),
    )

    result = workflow.monitor_positions(
        db=db,
        daily_market_data={
            "RELIANCE": {"open": 100, "high": 102, "low": 99, "close": 101, "signal": "HOLD"}
        },
        market_date=date(2026, 11, 12),
    )
    assert result["status"] == "SUCCESS"
    assert result["storage"]["positions_updated"] == 1
