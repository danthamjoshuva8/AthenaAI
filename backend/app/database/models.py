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

class StockMaster(Base):
    __tablename__ = "stock_master"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), unique=True, nullable=False)
    company_name = Column(String(200))
    sector = Column(String(100))
    industry = Column(String(200))