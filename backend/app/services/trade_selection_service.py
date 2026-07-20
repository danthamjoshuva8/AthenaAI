from typing import List

from sqlalchemy.orm import Session

from app.models.trade_candidate import TradeCandidate

from app.services.strategy_service import StrategyService

from app.utils.nifty200 import get_nifty200_symbols

from app.services.trade_ranking_service import (
    TradeRankingService
)

from app.services.position_sizing_service import (
    PositionSizingService
)

from app.services.market_context_service import (
    MarketContextService
)

from app.services.market_service import MarketService

from app.services.sector_strength_service import (
    SectorStrengthService
)

from app.database.models import StockMaster
from app.models.sector import Sector

class TradeSelectionService:

    """
    Converts strategy BUY signals into
    TradeCandidate objects.
    """
    def __init__(self):

        self.strategy = StrategyService()

        self.ranking = TradeRankingService()

        self.position_sizing = PositionSizingService()

        self.market_context = MarketContextService()

        self.market_service = MarketService()

        self.sector_strength = SectorStrengthService()

    def build_candidates(
        self,
        db: Session,
        symbol: str,
        signals: List[dict]
    ):

        candidates = []

        for signal in signals:

            if signal["signal"] != "BUY":
                continue

            entry = signal.get("entry_price")

            stop = signal.get("stop_loss")

            if entry is None or stop is None:
                continue

            risk = entry - stop

            if risk <= 0:
                continue

            candidate = TradeCandidate(

                symbol=symbol,

                signal_date=signal["date"],

                entry_price=entry,

                stop_loss=stop,

                risk_per_share=risk,

                target_2r=entry + (2 * risk),

                target_3r=entry + (3 * risk),

                volume_ratio=(
                    signal["volume"] / signal["volume20"]
                    if signal.get("volume20")
                    else 0
                ),

                distance_from_ma=signal.get(
                    "distance_from_ma",
                    0
                ),

                body_percent=signal.get(
                    "body_percent",
                    0
                ),

                volume_confirmation=signal.get(
                    "volume_confirmation",
                    False
                ),

                quality_pass=signal.get(
                    "quality_pass",
                    False
                ),

                metadata=signal

            )

            try:

                nifty_df = self.market_service.get_nifty_history(
                    db,
                    candidate.signal_date
                )

                nifty_df = self.market_service.prepare_nifty_context(
                    nifty_df
                )

                if not nifty_df.empty:

                    market_state = self.market_context.analyze(
                        nifty_df
                    )

                    candidate.market_score = (
                        market_state.total_score
                    )

                    stock = (
                        db.query(StockMaster)
                        .filter(StockMaster.symbol == symbol)
                        .first()
                    )

                    print("=" * 80)
                    print("Strategy Symbol :", symbol)

                    if stock:
                        print("DB Symbol       :", stock.symbol)
                        print("DB Sector       :", stock.sector)
                    else:
                        print("DB Result       : None")

                    candidate.sector = (
                        Sector(stock.sector)
                        if stock and stock.sector
                        else Sector.UNKNOWN
                    )

                    candidate.sector_score = (
                        self.sector_strength.get_sector_score(
                            db=db,
                            sector=candidate.sector,
                            signal_date=candidate.signal_date
                        )
                    )

                    print(
                        candidate.symbol,
                        candidate.sector,
                        candidate.sector_score
                    )

            except Exception as ex:

                print(
                    f"Market Context Error ({symbol}): {ex}"
                )

            candidate = self.position_sizing.calculate_position_size(

                candidate,

                portfolio_value=10000000,

                risk_percent=1

            )
            candidates.append(candidate)

        return candidates
    
    def scan_market(
        self,
        db: Session
    ):

        all_candidates = []

        symbols = get_nifty200_symbols()

        for symbol in symbols:

            try:

                signals = self.strategy.generate_signals(
                    db,
                    symbol
                )

                candidates = self.build_candidates(
                    db,
                    symbol,
                    signals
                )

                all_candidates.extend(
                    candidates
                )

            except Exception as ex:

                print(

                    f"Scan failed for {symbol}: {ex}"

                )

        return self.ranking.rank_candidates(
            all_candidates
        )