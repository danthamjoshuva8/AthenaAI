import pandas as pd
import yfinance as yf

from sqlalchemy.orm import Session

from app.database.models import MarketData
from app.schemas.market_data import HistoryLoadRequest
from datetime import datetime, date
from sqlalchemy import func
from app.utils.nifty200 import get_nifty200_symbols
from app.config.trade_quality_config import TradeQualityConfig
from app.config.sector_index_config import SECTOR_INDEX_SYMBOLS
from app.models.sector import Sector
import yfinance as yf

from app.database.models import StockMaster
from app.config.sector_mapping import YAHOO_TO_SECTOR
from app.models.sector import Sector
from app.utils.nifty200 import get_nifty200_symbols

class MarketService:

    def __init__(self):
        self.config = TradeQualityConfig().market_context

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
    
    def get_symbol_dataframe(
        self,
        db: Session,
        symbol: str
    ) -> pd.DataFrame:

        rows = (
            db.query(MarketData)
            .filter(MarketData.symbol == symbol)
            .order_by(MarketData.date)
            .all()
        )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                "Date": row.date,
                "Open": row.open,
                "High": row.high,
                "Low": row.low,
                "Close": row.close,
                "Volume": row.volume
            }
            for row in rows
        ])

        ma_column = f"MA{self.config.long_ma_period}"

        df[ma_column] = (
            df["Close"]
            .rolling(self.config.long_ma_period)
            .mean()
        )

        return df.dropna()
    
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
    
    def clear_market_data(
        self,
        db: Session
    ):
        
        count = db.query(MarketData).count()

        print("Rows before delete:", count)

        deleted = db.query(MarketData).delete()

        print("Deleted:", deleted)

        db.commit()

        count_after = db.query(MarketData).count()

        print("Rows after delete:", count_after)

        deleted = (

            db.query(MarketData)

            .delete()

        )

        db.commit()

        return {

            "message": "Market data cleared successfully",

            "rows_deleted": deleted

        }
    
    def get_market_context_data(self):

        df = self.download_history(
            symbol="^NSEI",
            period="1y"
        )

        if df.empty:
            return df

        df = df.copy()

        ma_period = self.config.long_ma_period

        ma_column = f"MA{ma_period}"

        df[ma_column] = (
            df["Close"]
            .rolling(ma_period)
            .mean()
        )

        df = df.dropna()

        print("NIFTY rows after MA:", len(df))

        return df
    
    def get_all_market_data(
        self,
        db: Session
    ) -> dict[str, pd.DataFrame]:

        market_data = {}

        symbols = get_nifty200_symbols()

        for symbol in symbols:

            try:

                df = self.get_symbol_dataframe(
                    db,
                    symbol
                )

                if (
                    df is not None
                    and not df.empty
                ):
                    market_data[symbol] = df

            except Exception as ex:

                print(
                    f"Market data load failed for {symbol}: {ex}"
                )

        return market_data
    
    def load_nifty_index_history(
        self,
        db: Session,
        years: int = 7
    ):

        symbol = "NIFTY50"

        print(f"Loading {symbol} history...")

        df = self.download_history(
            symbol="^NSEI",
            period=f"{years}y"
        )

        inserted = 0
        updated = 0

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

        return {

            "symbol": symbol,

            "inserted": inserted,

            "updated": updated,

            "total_rows": len(df)

        }
    
    def get_nifty_history(
        self,
        db: Session,
        signal_date: datetime.date
    ) -> pd.DataFrame:

        rows = (

            db.query(MarketData)

            .filter(
                MarketData.symbol == "NIFTY50",
                MarketData.date <= signal_date
            )

            .order_by(
                MarketData.date
            )

            .all()

        )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([

            {
                "Date": row.date,
                "Open": row.open,
                "High": row.high,
                "Low": row.low,
                "Close": row.close,
                "Volume": row.volume
            }

            for row in rows

        ])

        return df
    
    def prepare_nifty_context(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        if df.empty:
            return df

        df = df.copy()

        ma150 = self.config.long_ma_period

        # Moving Averages
        df[f"MA{ma150}"] = (
            df["Close"]
            .rolling(ma150)
            .mean()
        )

        df["MA20"] = (
            df["Close"]
            .rolling(20)
            .mean()
        )

        # 20-Day Momentum
        df["Momentum20"] = (
            (
                df["Close"]
                - df["Close"].shift(20)
            )
            / df["Close"].shift(20)
        ) * 100

        # True Range
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs()
        ], axis=1).max(axis=1)

        # ATR
        df["ATR20"] = (
            tr
            .rolling(20)
            .mean()
        )

        df["ATRPercent"] = (
            df["ATR20"]
            / df["Close"]
        ) * 100

        return df.dropna()
    
    def load_sector_history(
        self,
        db: Session,
        sector: Sector,
        years: int = 7
    ):

        yahoo_symbol = SECTOR_INDEX_SYMBOLS[sector]

        symbol = sector.value

        print(f"Loading {symbol} history...")

        df = self.download_history(
            symbol=yahoo_symbol,
            period=f"{years}y"
        )

        inserted = 0
        updated = 0

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

        return {

            "symbol": symbol,

            "inserted": inserted,

            "updated": updated,

            "total_rows": len(df)

        }

    def get_market_history(
        self,
        db: Session,
        symbol: str,
        end_date: date,
        lookback_days: int = 250
    ) -> pd.DataFrame:

        rows = (
            db.query(MarketData)
            .filter(
                MarketData.symbol == symbol,
                MarketData.date <= end_date
            )
            .order_by(MarketData.date)
            .all()
        )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                "Date": row.date,
                "Open": row.open,
                "High": row.high,
                "Low": row.low,
                "Close": row.close,
                "Volume": row.volume,
            }
            for row in rows
        ])

        df = df.sort_values("Date").reset_index(drop=True)
        return df
    
    def get_sector_history(
        self,
        db: Session,
        sector: Sector,
        signal_date: date
    ) -> pd.DataFrame:

        return self.get_market_history(
            db=db,
            symbol=sector.value,
            end_date=signal_date,
            lookback_days=250
        )
    
    def load_stock_master(
        self,
        db: Session
    ):

        symbols = get_nifty200_symbols()

        inserted = 0
        updated = 0

        for symbol in symbols:

            print(f"Loading {symbol}")

            try:

                ticker = yf.Ticker(symbol)

                info = ticker.info

                company_name = info.get("longName", "")

                yahoo_sector = info.get("sector", "")

                industry = info.get("industry", "")

                sector = YAHOO_TO_SECTOR.get(
                    yahoo_sector,
                    Sector.UNKNOWN
                )

                existing = (

                    db.query(StockMaster)

                    .filter(
                        StockMaster.symbol == symbol
                    )

                    .first()

                )

                if existing:

                    existing.company_name = company_name

                    existing.sector = sector.value

                    existing.industry = industry

                    updated += 1

                else:

                    db.add(

                        StockMaster(

                            symbol=symbol,

                            company_name=company_name,

                            sector=sector.value,

                            industry=industry

                        )

                    )

                    inserted += 1

            except Exception as ex:

                print(symbol, ex)
                raise

        db.commit()

        return {

            "inserted": inserted,

            "updated": updated,

            "total": len(symbols)

        }