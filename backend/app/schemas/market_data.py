
from datetime import date

from pydantic import BaseModel


class MarketDataResponse(BaseModel):
    """
    Defines the API response structure for historical market data.
    """

    symbol: str       # Stock or market index trading symbol.
    date: date        # Trading date of the market data.

    open: float       # Opening price for the trading session.
    high: float       # Highest price during the trading session.
    low: float        # Lowest price during the trading session.
    close: float      # Closing price for the trading session.

    volume: float     # Total trading volume during the session.

    class Config:
        """Enables model creation from ORM object attributes."""

        from_attributes = True


class HistoryLoadRequest(BaseModel):
    """
    Defines the API request parameters for loading historical market data.
    """

    years: int = 5    # Number of years of historical data to load.
