
from datetime import date

import pytest

from app.database.session import get_db
from app.forward_testing.storage import ForwardTestingRun
from app.forward_testing.forward_testing_storage_service import (
    ForwardTestingStorageService,
)


def test_daily_run_status_transitions():
    service = ForwardTestingStorageService()

    signal_date = date(2026, 11, 20)
    execution_date = date(2026, 11, 21)

    run_key = f"{signal_date.isoformat()}_{execution_date.isoformat()}"

    db_generator = get_db()
    db = next(db_generator)

    try:
        db.query(ForwardTestingRun).filter_by(
            run_key=run_key
        ).delete(synchronize_session=False)
        db.commit()

        created = service.start_daily_run(
            db, signal_date, execution_date
        )
        run_id = created["run_id"]

        # RUNNING -> SUCCESS must work
        service.complete_daily_run(
            db, run_id, {"test": "success"}
        )

        run = db.query(ForwardTestingRun).filter_by(
            id=run_id
        ).one()

        assert run.status == "SUCCESS"
        assert run.result == {"test": "success"}

        # SUCCESS -> FAILED must be rejected
        with pytest.raises(ValueError, match="current status is SUCCESS"):
            service.fail_daily_run(db, run_id, "late failure")

        run = db.query(ForwardTestingRun).filter_by(
            id=run_id
        ).one()
        assert run.status == "SUCCESS"

    finally:
        db_generator.close()


def test_failed_run_cannot_be_completed():
    service = ForwardTestingStorageService()

    signal_date = date(2026, 11, 22)
    execution_date = date(2026, 11, 23)

    run_key = f"{signal_date.isoformat()}_{execution_date.isoformat()}"

    db_generator = get_db()
    db = next(db_generator)

    try:
        db.query(ForwardTestingRun).filter_by(
            run_key=run_key
        ).delete(synchronize_session=False)
        db.commit()

        created = service.start_daily_run(
            db, signal_date, execution_date
        )
        run_id = created["run_id"]

        service.fail_daily_run(db, run_id, "simulated failure")

        # FAILED -> SUCCESS must be rejected
        with pytest.raises(ValueError, match="current status is FAILED"):
            service.complete_daily_run(
                db, run_id, {"test": "success"}
            )

        run = db.query(ForwardTestingRun).filter_by(
            id=run_id
        ).one()

        assert run.status == "FAILED"
        assert run.error_message == "simulated failure"

    finally:
        db_generator.close()


def test_complete_missing_run_raises_error():
    service = ForwardTestingStorageService()

    db_generator = get_db()
    db = next(db_generator)

    try:
        with pytest.raises(ValueError, match="not found"):
            service.complete_daily_run(
                db, -999999, {"test": "missing"}
            )
    finally:
        db_generator.close()


def test_fail_missing_run_raises_error():
    service = ForwardTestingStorageService()

    db_generator = get_db()
    db = next(db_generator)

    try:
        with pytest.raises(ValueError, match="not found"):
            service.fail_daily_run(
                db, -999999, "missing run"
            )
    finally:
        db_generator.close()
