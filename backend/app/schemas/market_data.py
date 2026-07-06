from datetime import date
from pydantic import BaseModel


class MarketDataResponse(BaseModel):

    symbol: str

    date: date

    open: float

    high: float

    low: float

    close: float

    volume: float

    class Config:

        from_attributes = True

class HistoryLoadRequest(BaseModel):
    years: int = 5