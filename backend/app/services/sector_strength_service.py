from app.config.trade_quality_config import TradeQualityConfig
from app.models.sector import Sector

from sqlalchemy.orm import Session
from app.services.market_service import MarketService
from app.services.market_context_service import MarketContextService


class SectorStrengthService:

    def __init__(self):

        self.config = TradeQualityConfig().sector

        self.market_service = MarketService()
        self.market_context_service = MarketContextService()

    def get_sector_score(
        self,
        db: Session,
        sector: Sector,
        signal_date
    ) -> float:

        try:

            if sector == Sector.UNKNOWN:
                return 0

            history = self.market_service.get_sector_history(
                db=db,
                sector=sector,
                signal_date=signal_date
            )

            if history.empty:
                print(f"[Sector] No history for {sector.value}")
                return 0

            history = self.market_service.prepare_nifty_context(history)

            if history.empty:
                print(f"[Sector] Not enough candles after indicators: {sector.value}")
                return 0
            
            print(history.tail(3)[[
                "Close",
                "MA20",
                "MA150",
                "Momentum20",
                "ATRPercent"
            ]])

            print("Rows before analyze:", len(history))

            market_state = self.market_context_service.analyze(history)

            print("Sector:", sector.value)
            print("Score:", market_state.total_score)

            print(
                f"[Sector] {sector.value} | "
                f"Trend={market_state.trend} | "
                f"Score={market_state.total_score}"
            )

            return float(market_state.total_score)

        except Exception as ex:

            print(f"[Sector Strength Error] {sector.value}: {ex}")

            return 0