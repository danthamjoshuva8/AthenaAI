import yfinance as yf

from sqlalchemy.orm import Session

from app.database.models import MarketData


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