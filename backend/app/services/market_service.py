import yfinance as yf

from sqlalchemy.orm import Session

from app.database.models import MarketData
from app.schemas.market_data import HistoryLoadRequest
from datetime import datetime, timedelta
from sqlalchemy import func
from app.utils.nifty200 import get_nifty200_symbols


class MarketService:

    def ping(self):

        return {
            "message": "Market Service Running"
        }

    def download_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ):

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period=period,
            interval=interval
        )

        return df

    def save_history(
        self,
        db: Session,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ):

        df = self.download_history(
            symbol,
            period,
            interval
        )

        count = 0

        for index, row in df.iterrows():

            record = MarketData(

                symbol=symbol,

                date=index.date(),

                open=float(row["Open"]),

                high=float(row["High"]),

                low=float(row["Low"]),

                close=float(row["Close"]),

                volume=float(row["Volume"])

            )

            db.add(record)

            count += 1

        db.commit()

        return count
    
    def get_all_data(
    self,
    db: Session):
        return db.query(MarketData).all()


    def get_symbol_data(
        self,
        db: Session,
        symbol: str
    ):

        return (

            db.query(MarketData)

            .filter(
                MarketData.symbol == symbol
            )

            .order_by(
                MarketData.date
            )

            .all()

        )
    
    def delete_symbol(
        self,
        db: Session,
        symbol: str
    ):

        deleted = (

            db.query(MarketData)

            .filter(
                MarketData.symbol == symbol
            )

            .delete()

        )

        db.commit()

        return deleted


    def statistics(
        self,
        db: Session
    ):

        total_rows = db.query(MarketData).count()

        symbols = db.query(
            MarketData.symbol
        ).distinct().count()

        return {

            "total_rows": total_rows,

            "symbols": symbols

        }
    
    def load_history(
        self,
        db: Session,
        years: int = 5
    ):

        return self.load_nifty200_history(
            db,
            years
        )
    
    def load_nifty200_history(
        self,
        db: Session,
        years: int = 5
    ):

        symbols = get_nifty200_symbols()

        print(f"Loading {len(symbols)} symbols...")

        processed = 0
        inserted = 0
        updated = 0
        failed = 0

        for symbol in symbols:
            print(f"[{processed + 1}/{len(symbols)}] {symbol}")

            try:

                processed += 1

                latest_date = (

                    db.query(
                        func.max(MarketData.date)
                    )

                    .filter(
                        MarketData.symbol == symbol
                    )

                    .scalar()

                )

                if latest_date is None:

                    period = f"{years}y"

                else:

                    period = "1mo"

                df = self.download_history(
                    symbol=symbol,
                    period=period
                )

                for index, row in df.iterrows():

                    trade_date = index.date()

                    existing = (

                        db.query(MarketData)

                        .filter(
                            MarketData.symbol == symbol,
                            MarketData.date == trade_date
                        )

                        .first()

                    )

                    if existing:

                        existing.open = float(row["Open"])
                        existing.high = float(row["High"])
                        existing.low = float(row["Low"])
                        existing.close = float(row["Close"])
                        existing.volume = float(row["Volume"])

                        updated += 1

                    else:

                        db.add(

                            MarketData(

                                symbol=symbol,

                                date=trade_date,

                                open=float(row["Open"]),

                                high=float(row["High"]),

                                low=float(row["Low"]),

                                close=float(row["Close"]),

                                volume=float(row["Volume"])

                            )

                        )

                        inserted += 1

                db.commit()

            except Exception:

                db.rollback()

                failed += 1

                continue

        return {

            "symbols": len(symbols),

            "processed": processed,

            "inserted": inserted,

            "updated": updated,

            "failed": failed

        }