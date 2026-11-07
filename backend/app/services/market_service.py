
from datetime import date

from sqlalchemy.orm import Session

from app.market.market_engine import MarketEngine
from app.models.sector import Sector


class MarketService:
    """
    Provides a service layer for market data operations, including
    historical data downloads, storage, retrieval, and sector analysis.
    """

    def __init__(self):
        """Initializes the market engine."""

        self.engine = MarketEngine()  # Engine responsible for market data operations.

    def ping(self):
        """Checks the market engine and data service connectivity."""
        return self.engine.ping()

    def download(self, symbol: str):
        """Downloads historical market data for the specified symbol."""
        return self.engine.download_history(symbol)

    def save_market_data(self, symbol: str, db: Session):
        """Downloads and saves historical market data to the database."""
        return self.engine.save_history(db, symbol)

    def get_all_market_data(self, db: Session):
        """Retrieves all available market data from the database."""
        return self.engine.get_all_data(db)

    def market_statistics(self, db: Session):
        """Retrieves market data statistics from the database."""
        return self.engine.statistics(db)

    def clear_market_data(self, db: Session):
        """Deletes all stored market data."""
        return self.engine.clear_market_data(db)

    def delete_symbol(self, symbol: str, db: Session):
        """Deletes historical market data for the specified symbol."""
        return self.engine.delete_symbol(db, symbol)

    def get_symbol_market_data(self, symbol: str, db: Session):
        """Retrieves historical market data for a specific symbol."""
        return self.engine.get_symbol_data(db, symbol)

    def load_history(self, years: int, db: Session, symbols: list):
        """Loads historical market data for the specified symbols and years."""
        return self.engine.load_history(db, symbols, years)

    def load_nifty50_history(self, years: int, db: Session):
        """Loads historical NIFTY 50 index data for the specified period."""
        return self.engine.load_nifty_index_history(db, years)

    def test_nifty(self, date: date, db: Session):
        """
        Retrieves and prepares NIFTY historical data for a given date.
        Returns row count, latest date, closing price, and MA150 value.
        """

        df = self.engine.get_nifty_history(db, date)

        df = self.engine.prepare_nifty_context(df)

        return {
            "rows": len(df),
            "last_date": str(df.iloc[-1]["Date"]),
            "last_close": float(df.iloc[-1]["Close"]),
            "last_ma150": float(df.iloc[-1]["MA150"])
        }

    def load_sector_history(
        self,
        sector: Sector,
        years: int,
        db: Session
    ):
        """Loads historical stock data belonging to the specified sector."""
        return self.engine.load_sector_history(
            db=db,
            sector=sector,
            years=years
        )

    def load_stock_master(self, db: Session, symbols: list):
        """Loads or updates master information for the specified stocks."""
        return self.engine.load_stock_master(db, symbols)
