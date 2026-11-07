"""
Exit Strategy Factory for AthenaAI.

Creates the appropriate exit strategy based on the configured
ExitStrategyType.

Supported strategies:
    - PARTIAL_2R_3R
    - FULL_3R
    - TRAIL_2R
    - TRAIL_2R_CLOSE
    - TARGET_2R

Responsibilities:
    - Validate the requested exit strategy.
    - Initialize the corresponding strategy implementation.
    - Log strategy selection and initialization events.

The factory does not execute exit calculations or modify positions.

Caching:
    Strategy instances are not cached.
    Each factory call creates a fresh strategy instance.
"""

import logging
from time import perf_counter
from typing import Any

from app.config.backtest_config import ExitStrategyType

from .full_3r_strategy import Full3RStrategy
from .partial_exit_strategy import PartialExitStrategy
from .target_2r_strategy import Target2RStrategy
from .trail_2r_close_strategy import Trail2RCloseStrategy
from .trail_2r_strategy import Trail2RStrategy


logger = logging.getLogger(__name__)


class ExitStrategyFactory:
    """
    Factory responsible for creating backtesting exit strategies.

    Maps each ExitStrategyType to its corresponding implementation.
    """

    @staticmethod
    def create(strategy: ExitStrategyType) -> Any:
        """
        Create an exit strategy based on the requested strategy type.

        Args:
            strategy: ExitStrategyType identifying the exit strategy.

        Returns:
            An initialized exit strategy instance.

        Raises:
            ValueError: If the requested strategy is unknown.
            Exception: If strategy initialization fails unexpectedly.
        """

        start_time = perf_counter()

        strategy_mapping = {
            ExitStrategyType.PARTIAL_2R_3R: PartialExitStrategy,
            ExitStrategyType.FULL_3R: Full3RStrategy,
            ExitStrategyType.TRAIL_2R: Trail2RStrategy,
            ExitStrategyType.TRAIL_2R_CLOSE: Trail2RCloseStrategy,
            ExitStrategyType.TARGET_2R: Target2RStrategy,
        }

        strategy_name = getattr(strategy, "name", str(strategy))

        logger.info(
            "Exit strategy initialization started",
            extra={
                "event": "exit_strategy_initialization_started",
                "strategy": strategy_name,
            },
        )

        try:
            strategy_class = strategy_mapping.get(strategy)

            if strategy_class is None:
                logger.error(
                    "Unknown exit strategy requested",
                    extra={
                        "event": "exit_strategy_unsupported",
                        "strategy": strategy_name,
                        "status": "unsupported",
                    },
                )

                raise ValueError(
                    f"Unknown exit strategy: {strategy_name}"
                )

            instance = strategy_class()

            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.info(
                "Exit strategy initialized successfully",
                extra={
                    "event": "exit_strategy_initialization_completed",
                    "strategy": strategy_name,
                    "strategy_class": strategy_class.__name__,
                    "status": "success",
                    "duration_ms": duration_ms,
                },
            )

            return instance

        except ValueError:
            raise

        except Exception:
            duration_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "Exit strategy initialization failed",
                extra={
                    "event": "exit_strategy_initialization_failed",
                    "strategy": strategy_name,
                    "status": "failed",
                    "duration_ms": duration_ms,
                },
            )

            raise