from app.config.trade_quality_config import TradeQualityConfig
from app.models.sector import Sector
from app.services.market_service import MarketService
from sqlalchemy.orm import Session

from app.market.market_analyzer import MarketAnalyzer
from app.market.market_engine import MarketEngine


class SectorAnalyzer:
    """
    Analyzes sector performance using historical sector data and
    market context indicators.

    Uses the market analysis engine to prepare sector history and
    the market analyzer to calculate the sector's overall score.
    """

    def __init__(self):
        """
        Initialize sector analysis configuration and dependencies.

        Loads sector-specific quality configuration and creates
        the market engine and market context analyzer.
        """

        # Load the sector-specific trade quality configuration.
        self.config = TradeQualityConfig().sector

        # Initialize the engine responsible for retrieving and preparing
        # historical sector market data.
        self.market_engine = MarketEngine()

        # Initialize the analyzer used to evaluate market conditions.
        self.market_context_service = MarketAnalyzer()

    def get_sector_score(
        self,
        db: Session,
        sector: Sector,
        signal_date
    ) -> float:
        """
        Calculate the market strength score for a given sector.

        Retrieves historical sector data up to the signal date,
        prepares the market indicators, and evaluates the resulting
        market conditions.

        Args:
            db: SQLAlchemy database session used to retrieve sector history.
            sector: Sector whose market strength needs to be evaluated.
            signal_date: Date used to determine the relevant sector history.

        Returns:
            The sector's total market analysis score as a float.
            Returns 0 when the sector is unknown, historical data is
            unavailable, indicators cannot be prepared, or an exception occurs.
        """

        try:
            # Skip sector analysis when the candidate's sector is unknown.
            if sector == Sector.UNKNOWN:
                return 0

            # Retrieve historical data for the sector up to the signal date.
            history = self.market_engine.get_sector_history(
                db=db,
                sector=sector,
                signal_date=signal_date
            )

            # Stop analysis when no historical sector data is available.
            if history.empty:
                print(f"[Sector] No history for {sector.value}")
                return 0

            # Prepare the historical data with NIFTY market context indicators.
            history = self.market_engine.prepare_nifty_context(history)

            # Stop analysis when there are insufficient candles for indicators.
            if history.empty:
                print(f"[Sector] Not enough candles after indicators: {sector.value}")
                return 0

            # Analyze the prepared sector data to obtain its market state.
            market_state = self.market_context_service.analyze(history)

            # Return the overall market analysis score for the sector.
            return float(market_state.total_score)

        except Exception as ex:
            # Report sector analysis failures and return a default score.
            print(f"[Sector Strength Error] {sector.value}: {ex}")

            return 0