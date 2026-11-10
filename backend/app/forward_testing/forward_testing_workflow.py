
from datetime import date

from sqlalchemy.orm import Session

from app.config.backtest_config import ExitStrategyType

from app.forward_testing.portfolio_manager import (
    ForwardTestingPortfolioManager,
)
from app.forward_testing.paper_execution_engine import (
    PaperExecutionEngine,
)
from app.forward_testing.position_manager import (
    ForwardTestingPositionManager,
)
from app.forward_testing.forward_testing_storage_service import (
    ForwardTestingStorageService,
)


class ForwardTestingWorkflow:
    """
    Coordinates AthenaAI's forward-testing workflow.

    Connects portfolio approval, paper execution,
    position management and persistent storage.
    """

    def __init__(self):
        self.portfolio_manager = ForwardTestingPortfolioManager()

        self.execution_engine = PaperExecutionEngine(
            slippage_bps=5,
            brokerage_pct=0.0,
        )

        self.position_manager = ForwardTestingPositionManager(
            exit_strategy=ExitStrategyType.PARTIAL_2R_3R
        )

        self.storage_service = ForwardTestingStorageService()

    
    def execute_daily_orders(
        self,
        db: Session,
        ranked_candidates: list[dict],
        available_capital: float,
        entries_today: int,
        next_session_market_data: dict,
        signal_date: date,
        execution_date: date,
    ) -> dict:

        run = self.storage_service.start_daily_run(
            db=db,
            signal_date=signal_date,
            execution_date=execution_date,
        )

        if not run["created"]:
            return {
                "status": "SKIPPED",
                "message": f"Run already exists with status: {run['status']}",
                "run_id": run["run_id"],
                "run_key": run["run_key"],
            }

        run_id = run["run_id"]

        try:
            current_positions = self.storage_service.get_open_positions(db)

            portfolio_result = self.portfolio_manager.evaluate_candidates(
                candidates=ranked_candidates,
                current_positions=current_positions,
                available_capital=available_capital,
                entries_today=entries_today,
            )

            execution_result = self.execution_engine.execute_orders(
                approved_positions=portfolio_result["accepted"],
                market_data_by_symbol=next_session_market_data,
                execution_date=execution_date,
            )

            initialization_result = self.position_manager.initialize_positions(
                execution_result
            )

            storage_result = self.storage_service.save_execution_and_positions(
                db=db,
                execution_result=execution_result,
                initialization_result=initialization_result,
                run_id=run_id,
            )

            if storage_result["status"] != "SUCCESS":
                raise RuntimeError(
                    "Failed to save paper execution results"
                )

            final_result = {
                "status": "SUCCESS",
                "signal_date": signal_date.isoformat(),
                "execution_date": execution_date.isoformat(),
                "portfolio": portfolio_result,
                "execution": execution_result,
                "position_initialization": initialization_result,
                "storage": storage_result,
            }

            # Mark the run SUCCESS within the same transaction.
            self.storage_service.complete_daily_run(
                db=db,
                run_id=run_id,
                result={
                    "orders_saved": storage_result["orders_saved"],
                    "positions_saved": storage_result["positions_saved"],
                },
            )

            # Commit orders, positions and SUCCESS status together.
            db.commit()

            return final_result

        except Exception as exc:
            # Roll back all execution persistence and SUCCESS changes.
            db.rollback()

            # Record FAILED in a separate transaction.
            self.storage_service.fail_daily_run(
                db=db,
                run_id=run_id,
                error_message=str(exc),
            )

            raise

    def monitor_positions(
        self,
        db: Session,
        daily_market_data: dict,
        market_date: date,
    ) -> dict:
        """
        Monitor persisted open positions using completed daily candles.

        Updates PostgreSQL with position changes and exit events.
        """

        # Step 1: Retrieve persisted open positions.
        open_positions = self.storage_service.get_open_positions(db)

        if not open_positions:
            return {
                "status": "SUCCESS",
                "market_date": market_date.isoformat(),
                "message": "No open positions to monitor.",
                "positions_processed": 0,
            }

        # Step 2: Process stop-loss, targets and exit strategies.
        position_result = self.position_manager.process_positions(
            positions=open_positions,
            market_data_by_symbol=daily_market_data,
            market_date=market_date,
        )

        # Step 3: Persist updated positions and exit events.
        storage_result = self.storage_service.update_position_results(
            db=db,
            position_result=position_result,
        )

        return {
            "status": "SUCCESS",
            "position_result": position_result,
            "storage": storage_result,
        }
