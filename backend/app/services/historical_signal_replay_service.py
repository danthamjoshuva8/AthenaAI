
from datetime import date

from sqlalchemy.orm import Session

from app.database.models import MarketData
from app.market.symbol_provider import load_nifty200_symbols
from app.trade_selection.trade_selection_engine import TradeSelectionEngine


class HistoricalSignalReplayService:

    def __init__(self):

        self.engine = TradeSelectionEngine()

    def scan(
        self,
        db: Session,
        scan_date: date
    ) -> dict:

        symbols = load_nifty200_symbols()

        if not symbols:
            raise ValueError("NIFTY 200 symbol universe is empty.")

        symbols = list(dict.fromkeys(symbols))

        symbols_scanned = 0
        symbols_without_data = 0
        symbols_failed = 0

        buy_signals = 0
        sell_signals = 0
        hold_signals = 0

        all_candidates = []

        for symbol in symbols:

            try:

                # Confirm that this symbol has data on the requested date.
                has_data = (
                    db.query(MarketData.id)
                    .filter(
                        MarketData.symbol == symbol,
                        MarketData.date == scan_date
                    )
                    .first()
                )

                if not has_data:
                    symbols_without_data += 1
                    continue

                # Generate signals using data only up to scan_date.
                signals = self.engine.strategy.generate_signals(
                    db=db,
                    symbol=symbol,
                    end_date=scan_date
                )

                # Get the signal belonging to the requested date.
                historical_signal = next(
                    (
                        signal
                        for signal in reversed(signals)
                        if signal["date"] == scan_date
                    ),
                    None
                )

                if historical_signal is None:
                    symbols_without_data += 1
                    continue

                symbols_scanned += 1

                signal_type = historical_signal["signal"]

                if signal_type == "BUY":

                    buy_signals += 1

                    candidates = self.engine.build_candidates(
                        db=db,
                        symbol=symbol,
                        signals=[historical_signal]
                    )

                    all_candidates.extend(candidates)

                elif signal_type == "SELL":

                    sell_signals += 1

                else:

                    hold_signals += 1

            except Exception:

                symbols_failed += 1

        # Rank BUY candidates using the existing ranking engine.
        ranked_candidates = self.engine.ranking.rank_candidates(
            all_candidates
        )

        return {
            "scan_date": scan_date.isoformat(),
            "universe_size": len(symbols),
            "symbols_scanned": symbols_scanned,
            "symbols_without_data": symbols_without_data,
            "symbols_failed": symbols_failed,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "hold_signals": hold_signals,
            "candidates_count": len(ranked_candidates),
            "candidates": ranked_candidates
        }
