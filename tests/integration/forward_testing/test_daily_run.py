
from datetime import date, timedelta

from app.database.session import get_db
from app.forward_testing.storage import ForwardTestingRun
from app.forward_testing.forward_testing_storage_service import (
    ForwardTestingStorageService,
)


def test_daily_run_creation():
    storage_service = ForwardTestingStorageService()

    # Use a deterministic date pair for this test
    signal_date = date(2026, 11, 10)
    execution_date = date(2026, 11, 11)

    run_key = f"{signal_date.isoformat()}_{execution_date.isoformat()}"

    db_generator = get_db()
    db = next(db_generator)

    try:
        # CLEANUP: Remove an old record from previous test executions
        db.query(ForwardTestingRun).filter(
            ForwardTestingRun.run_key == run_key
        ).delete(synchronize_session=False)
        db.commit()

        # TEST 1: Create a new daily run
        first_result = storage_service.start_daily_run(
            db=db,
            signal_date=signal_date,
            execution_date=execution_date,
        )

        print("\nTEST 1 - Daily Run Creation")
        print(first_result)

        assert first_result["created"] is True
        assert first_result["status"] == "RUNNING"

        # TEST 2: Prevent duplicate daily run
        second_result = storage_service.start_daily_run(
            db=db,
            signal_date=signal_date,
            execution_date=execution_date,
        )

        print("\nTEST 2 - Duplicate Prevention")
        print(second_result)

        assert second_result["created"] is False
        assert second_result["run_id"] == first_result["run_id"]

        print("\nSUCCESS: Both tests passed!")

    finally:
        db_generator.close()
