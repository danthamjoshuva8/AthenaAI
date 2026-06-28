from sqlalchemy import Column, Integer, Float, String, Date

from app.database.base import Base


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)

    symbol = Column(String(20), nullable=False)

    date = Column(Date, nullable=False)

    open = Column(Float)

    high = Column(Float)

    low = Column(Float)

    close = Column(Float)

    volume = Column(Float)