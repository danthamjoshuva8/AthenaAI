
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.database.models import MarketData
from app.forward_testing.signal_processor import (
    ForwardTestingSignalProcessor,
)
from app.forward_testing.forward_testing_workflow import (
    ForwardTestingWorkflow,
)


logger = logging.getLogger(__name__)


class ForwardTestingService:

    def __init__(self):
        self.signal_processor = ForwardTestingSignalProcessor()
        self.workflow = ForwardTestingWorkflow()

    def scan_latest_session(self, db: Session) -> dict:
        return self.signal_processor.scan_latest_session(db)

    @staticmethod
    def get_market_data(
        db: Session,
        symbols: list[str],
        market_date: date,
    ) -> dict:
        rows = (
            db.query(MarketData)
            .filter(
                MarketData.symbol.in_(symbols),
                MarketData.date == market_date,
            )
            .all()
        )

        result = {}

        for row in rows:
            result[row.symbol] = {
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
            }

        return result

    @staticmethod
    def get_available_capital(db: Session) -> float:
        # TODO: Connect this to your actual portfolio capital configuration.
        raise NotImplementedError(
            "Configure available paper-trading capital."
        )

    def execute_daily_orders(
        self,
        db: Session,
        signal_date: date,
        execution_date: date,
    ) -> dict:

        scan_result = self.scan_latest_session(db)

        if scan_result["scan_date"] != signal_date.isoformat():
            return {
                "status": "SKIPPED",
                "message": "Signal date does not match requested date.",
            }

        candidates = scan_result["candidates"]

        if not candidates:
            return {
                "status": "SKIPPED",
                "message": "No eligible BUY candidates.",
                "signal_date": signal_date.isoformat(),
            }

        symbols = list({
            candidate.symbol
            for candidate in candidates
        })

        market_data = self.get_market_data(
            db,
            symbols,
            execution_date,
        )

        if not market_data:
            return {
                "status": "WAITING_FOR_MARKET_DATA",
                "execution_date": execution_date.isoformat(),
                "message": "Execution-day market data is not available.",
            }

        available_capital = self.get_available_capital(db)

        open_positions = self.workflow.storage_service.get_open_positions(db)

        execution_result = self.workflow.execute_daily_orders(
            db=db,
            ranked_candidates=candidates,
            available_capital=available_capital,
            entries_today=0,
            next_session_market_data=market_data,
            signal_date=signal_date,
            execution_date=execution_date,
        )

        return execution_result

    def monitor_positions(
        self,
        db: Session,
        market_date: date,
    ) -> dict:

        positions = self.workflow.storage_service.get_open_positions(db)

        if not positions:
            return {
                "status": "SUCCESS",
                "positions_processed": 0,
                "market_date": market_date.isoformat(),
            }

        symbols = list({
            position["symbol"]
            for position in positions
        })

        market_data = self.get_market_data(
            db,
            symbols,
            market_date,
        )

        if not market_data:
            return {
                "status": "WAITING_FOR_MARKET_DATA",
                "market_date": market_date.isoformat(),
            }

        return self.workflow.monitor_positions(
            db=db,
            daily_market_data=market_data,
            market_date=market_date,
        )
