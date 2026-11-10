from datetime import date

from app.forward_testing.forward_testing_storage_service import ForwardTestingStorageService
from app.forward_testing.storage import ForwardTestingRun


def test_daily_run_create_and_duplicate_guard(db):
    service = ForwardTestingStorageService()
    signal_date = date(2026, 11, 10)
    execution_date = date(2026, 11, 11)

    first = service.start_daily_run(db, signal_date, execution_date)
    second = service.start_daily_run(db, signal_date, execution_date)

    assert first["created"] is True
    assert first["status"] == "RUNNING"
    assert second["created"] is False
    assert second["run_id"] == first["run_id"]
    assert db.query(ForwardTestingRun).count() == 1



def test_failed_run_is_not_automatically_restarted(db):
    service = ForwardTestingStorageService()
    signal_date = date(2026, 11, 12)
    execution_date = date(2026, 11, 13)

    first = service.start_daily_run(db, signal_date, execution_date)

    service.fail_daily_run(
        db,
        first["run_id"],
        "simulated failure",
    )

    failed = (
        db.query(ForwardTestingRun)
        .filter_by(id=first["run_id"])
        .one()
    )

    assert failed.status == "FAILED"
    assert failed.error_message == "simulated failure"

    second = service.start_daily_run(
        db,
        signal_date,
        execution_date,
    )

    assert second["created"] is False
    assert second["run_id"] == first["run_id"]
    assert second["status"] == "FAILED"

    refreshed = (
        db.query(ForwardTestingRun)
        .filter_by(id=first["run_id"])
        .one()
    )

    assert refreshed.status == "FAILED"
    assert refreshed.error_message == "simulated failure"

    assert db.query(ForwardTestingRun).filter_by(
        run_key=first["run_key"]
    ).count() == 1


def test_successful_run_is_not_restarted(db):
    service = ForwardTestingStorageService()
    signal_date = date(2026, 11, 14)
    execution_date = date(2026, 11, 16)

    first = service.start_daily_run(db, signal_date, execution_date)
    service.complete_daily_run(db, first["run_id"], {"orders_saved": 2})

    second = service.start_daily_run(db, signal_date, execution_date)
    assert second["created"] is False
    assert second["status"] == "SUCCESS"
    assert second["result"] == {"orders_saved": 2}
