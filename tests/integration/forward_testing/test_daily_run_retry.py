
from datetime import date

from app.database.session import get_db
from app.forward_testing.storage import ForwardTestingRun
from app.forward_testing.forward_testing_storage_service import (
    ForwardTestingStorageService,
)


def test_failed_daily_run_is_not_automatically_restarted():
    storage_service = ForwardTestingStorageService()

    signal_date = date(2026, 11, 12)
    execution_date = date(2026, 11, 13)

    run_key = f"{signal_date.isoformat()}_{execution_date.isoformat()}"

    db_generator = get_db()
    db = next(db_generator)

    try:
        # Clean up previous test execution
        db.query(ForwardTestingRun).filter(
            ForwardTestingRun.run_key == run_key
        ).delete(synchronize_session=False)
        db.commit()

        # Create initial run
        first_result = storage_service.start_daily_run(
            db=db,
            signal_date=signal_date,
            execution_date=execution_date,
        )

        assert first_result["created"] is True

        run_id = first_result["run_id"]

        # Mark the run as failed
        storage_service.fail_daily_run(
            db=db,
            run_id=run_id,
            error_message="Test failure",
        )

        failed_run = (
            db.query(ForwardTestingRun)
            .filter_by(id=run_id)
            .one()
        )

        assert failed_run.status == "FAILED"
        assert failed_run.error_message == "Test failure"

        # Attempt to start the same run again
        retry_result = storage_service.start_daily_run(
            db=db,
            signal_date=signal_date,
            execution_date=execution_date,
        )

        print("\nFAILED RUN RESTART CHECK")
        print(retry_result)

        # Existing failed run must not restart automatically
        assert retry_result["created"] is False
        assert retry_result["run_id"] == run_id
        assert retry_result["status"] == "FAILED"

        # Verify the database was not modified
        refreshed_run = (
            db.query(ForwardTestingRun)
            .filter_by(id=run_id)
            .one()
        )

        assert refreshed_run.status == "FAILED"
        assert refreshed_run.error_message == "Test failure"

        assert (
            db.query(ForwardTestingRun)
            .filter_by(run_key=run_key)
            .count()
            == 1
        )

        print("\nSUCCESS: Failed run was not automatically restarted!")

    finally:
        db_generator.close()
