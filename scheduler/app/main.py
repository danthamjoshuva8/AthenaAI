
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.forward_testing_job import (
    run_candidate_scan,
    run_position_monitoring,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def start_scheduler():

    scheduler = BlockingScheduler(timezone=IST)

    # Scan after market close.
    scheduler.add_job(
        run_candidate_scan,
        CronTrigger(
            day_of_week="mon-fri",
            hour=15,
            minute=45,
            timezone=IST,
        ),
        id="daily_candidate_scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Monitor positions after the daily market-data update.
    # Adjust this time to your actual data update schedule.
    scheduler.add_job(
        run_position_monitoring,
        CronTrigger(
            day_of_week="mon-fri",
            hour=18,
            minute=30,
            timezone=IST,
        ),
        id="daily_position_monitoring",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    logger.info("AthenaAI scheduler started")

    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
