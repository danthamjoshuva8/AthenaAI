
import logging
import time
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import MarketData
from app.market.symbol_provider import load_nifty200_symbols
from app.trade_selection.trade_selection_engine import TradeSelectionEngine


logger = logging.getLogger(__name__)


class ForwardTestingSignalProcessor:
    """
    Process only the latest available market session for forward testing.

    Reuses AthenaAI's existing:
        - StrategyService
        - TradeSelectionEngine
        - TradeQualityEngine
        - TradeRankingEngine
        - PositionSizer

    Historical BUY signals are not treated as new forward-testing signals.
    """

    def __init__(self, trade_selection_engine=None):
        self.trade_selection = (
            trade_selection_engine
            or TradeSelectionEngine()
        )

    @staticmethod
    def _to_date(value) -> date:
        """Convert supported date values into Python date objects."""

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if hasattr(value, "date") and callable(value.date):
            return value.date()

        return date.fromisoformat(str(value)[:10])

    def _get_latest_market_dates(
        self,
        db: Session,
        symbols: list[str]
    ) -> dict:
        """
        Retrieve the latest available candle date for each symbol.
        """

        rows = (
            db.query(
                MarketData.symbol,
                func.max(MarketData.date).label("latest_date")
            )
            .filter(MarketData.symbol.in_(symbols))
            .group_by(MarketData.symbol)
            .all()
        )

        return {
            symbol: self._to_date(latest_date)
            for symbol, latest_date in rows
            if latest_date is not None
        }

    def scan_latest_session(self, db: Session) -> dict:
        """
        Generate BUY candidates exclusively from the latest market session.
        """

        started_at = time.perf_counter()

        symbols = load_nifty200_symbols()

        if not symbols:
            raise ValueError(
                "NIFTY 200 symbol universe is empty."
            )

        latest_dates = self._get_latest_market_dates(
            db,
            symbols
        )

        if not latest_dates:
            raise ValueError(
                "No market data available for NIFTY 200."
            )

        scan_date = max(latest_dates.values())

        all_candidates = []

        scanned_symbols = 0
        buy_signals_found = 0

        stale_symbols = []
        symbols_without_data = []
        failed_symbols = []

        logger.info(
            "Forward-testing scan started",
            extra={
                "event": "forward_testing_scan_started",
                "scan_date": scan_date.isoformat(),
                "universe_size": len(symbols)
            }
        )

        for symbol in symbols:

            symbol_latest_date = latest_dates.get(symbol)

            # No historical candles available.
            if symbol_latest_date is None:
                symbols_without_data.append(symbol)
                continue

            # Do not generate signals from stale market data.
            if symbol_latest_date != scan_date:
                stale_symbols.append(symbol)
                continue

            try:

                # Reuse the existing strategy engine.
                signals = (
                    self.trade_selection.strategy.generate_signals(
                        db,
                        symbol
                    )
                )

                scanned_symbols += 1

                if not signals:
                    continue

                # Only the most recent generated signal is eligible.
                latest_signal = signals[-1]

                signal_date = self._to_date(
                    latest_signal["date"]
                )

                if signal_date != scan_date:
                    failed_symbols.append({
                        "symbol": symbol,
                        "reason": (
                            "Latest signal date does not match "
                            "the latest market session."
                        )
                    })
                    continue

                # Only fresh BUY signals are eligible.
                if latest_signal.get("signal") != "BUY":
                    continue

                buy_signals_found += 1

                # Reuse existing candidate-building logic.
                candidates = (
                    self.trade_selection.build_candidates(
                        db=db,
                        symbol=symbol,
                        signals=[latest_signal]
                    )
                )

                all_candidates.extend(candidates)

            except Exception as exc:

                failed_symbols.append({
                    "symbol": symbol,
                    "reason": str(exc)
                })

                logger.exception(
                    "Forward-testing signal processing failed",
                    extra={
                        "event": "forward_testing_symbol_failed",
                        "symbol": symbol,
                        "scan_date": scan_date.isoformat()
                    }
                )

        # Reuse existing ranking engine.
        ranked_candidates = (
            self.trade_selection.ranking.rank_candidates(
                all_candidates
            )
        )

        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2
        )

        result = {
            "scan_date": scan_date.isoformat(),
            "universe_size": len(symbols),
            "symbols_scanned": scanned_symbols,
            "symbols_skipped_stale": len(stale_symbols),
            "symbols_without_data": len(symbols_without_data),
            "symbols_failed": len(failed_symbols),
            "latest_buy_signals": buy_signals_found,
            "candidates_count": len(ranked_candidates),
            "duration_ms": duration_ms,
            "stale_symbols": stale_symbols,
            "symbols_without_data_list": symbols_without_data,
            "failed_symbols": failed_symbols,
            "candidates": ranked_candidates
        }

        logger.info(
            "Forward-testing scan completed",
            extra={
                "event": "forward_testing_scan_completed",
                "scan_date": scan_date.isoformat(),
                "symbols_scanned": scanned_symbols,
                "latest_buy_signals": buy_signals_found,
                "candidates_count": len(ranked_candidates),
                "duration_ms": duration_ms
            }
        )

        return result
