from datetime import date, datetime, timedelta, time

import pandas as pd
import yfinance as yf
from app.config.sector_index_config import SECTOR_INDEX_SYMBOLS
from app.config.sector_mapping import YAHOO_TO_SECTOR
from app.config.trade_quality_config import TradeQualityConfig
from app.database.models import MarketData, StockMaster
from app.models.sector import Sector
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging
from app.core.cache import cache_manager
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class MarketEngine:

    def __init__(self):
        self.config = TradeQualityConfig().market_context

    
    def ping(self) -> dict:
        """
        Check whether the Market Service is responding.

        This function returns a simple health message to confirm
        that the Market Service endpoint is accessible.

        Execution Steps:
            1. Log the health-check request.
            2. Prepare the service status response.
            3. Log successful completion.
            4. Return the response.

        Returns:
            dict: Market Service health status.
        """

        # Step 1: Log the health-check request.
        logger.debug(
            "Market service health check requested",
            extra={
                "event": "market_service_ping"
            }
        )

        # Step 2: Prepare the service response.
        response = {
            "message": "Market Service Running"
        }

        # Step 3: Log successful completion.
        logger.info(
            "Market service health check successful",
            extra={
                "event": "market_service_ping_success"
            }
        )

        # Step 4: Return the service status.
        return response

    def download_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        start: date = None,
        end: date = None
    ) -> list[dict]:
        """
        Download historical OHLCV data with Redis caching.

        Supports period-based downloads for initial history loading
        and date-based downloads for incremental market data updates.

        Execution Steps:
            1. Validate the stock symbol and download parameters.
            2. Generate a unique Redis cache key.
            3. Check Redis for previously downloaded market data.
            4. Return cached data if available.
            5. Download market history from Yahoo Finance on a cache miss.
            6. Check whether Yahoo Finance returned valid data.
            7. Convert the DataFrame into dictionary records.
            8. Store the downloaded records in Redis.
            9. Return historical market data.

        Args:
            symbol: Yahoo Finance stock symbol, e.g. RELIANCE.NS.
            period: Historical data period, e.g. 1y or 5y.
            interval: Candle interval, e.g. 1d or 1h.
            start: Inclusive start date for incremental downloads.
            end: Exclusive end date for incremental downloads.

        Returns:
            list[dict]: Historical OHLCV records.

        Raises:
            ValueError: If the supplied parameters are invalid.
            RuntimeError: If Yahoo Finance download fails.

        Notes:
            Redis failures do not prevent downloading market data.
            Cached data is temporary and expires according to TTL.
            Date-based downloads take precedence over period-based downloads.
        """

        # Step 1: Validate input parameters.
        if not symbol or not symbol.strip():
            raise ValueError("Stock symbol cannot be empty")

        if not interval:
            raise ValueError("Interval is required")

        if start is not None and end is not None and start >= end:
            raise ValueError("Start date must be earlier than end date")

        if (start is None) != (end is None):
            raise ValueError("Both start and end dates are required")

        if start is None and not period:
            raise ValueError("Period is required for historical downloads")

        symbol = symbol.strip().upper()

        # Step 2: Generate a unique cache key.
        if start is not None and end is not None:
            cache_key = (
                f"athena:market:history:"
                f"{symbol}:{start}:{end}:{interval}:v2"
            )
        else:
            cache_key = (
                f"athena:market:history:"
                f"{symbol}:{period}:{interval}:v1"
            )

        # Step 3: Check Redis for existing market history.
        cached_data = cache_manager.get_json(cache_key)

        # Step 4: Return cached records when available.
        if cached_data is not None:

            logger.info(
                "Market history retrieved from Redis",
                extra={
                    "event": "market_history_cache_hit",
                    "symbol": symbol,
                    "period": period if start is None else None,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "interval": interval,
                    "cache_status": "HIT"
                }
            )

            return cached_data

        # Step 5: Cache miss - download from Yahoo Finance.
        logger.info(
            "Downloading market history from Yahoo Finance",
            extra={
                "event": "market_history_download_started",
                "symbol": symbol,
                "period": period if start is None else None,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                "interval": interval,
                "cache_status": "MISS"
            }
        )

        try:

            # Step 6: Initialize Yahoo Finance ticker.
            ticker = yf.Ticker(symbol)

            # Step 7: Download historical OHLCV data.
            if start is not None and end is not None:
                df = ticker.history(
                    start=start.isoformat(),
                    end=end.isoformat(),
                    interval=interval
                )
            else:
                df = ticker.history(
                    period=period,
                    interval=interval
                )

            logger.info(
                "Yahoo Finance raw history dates",
                extra={
                    "symbol": symbol,
                    "index": [
                        str(value)
                        for value in df.index[-5:]
                    ],
                    "timezone": str(df.index.tz)
                }
            )

            # Step 8: Check whether data was returned.
            if df.empty:

                logger.warning(
                    "Yahoo Finance returned no market history",
                    extra={
                        "event": "market_history_empty",
                        "symbol": symbol,
                        "period": period if start is None else None,
                        "start": start.isoformat() if start else None,
                        "end": end.isoformat() if end else None,
                        "interval": interval
                    }
                )

                return []

            # Step 9: Convert DataFrame into dictionary records.
            # Reset the index to include Date/Datetime in each record.
            df = df.reset_index()

            records = df.to_dict(
                orient="records"
            )

            # Step 10: Store downloaded history in Redis.
            # One hour is the initial TTL for daily history.
            # For intraday history, use a shorter TTL.
            ttl = 3600 if interval == "1d" else 900

            cache_manager.set_json(
                cache_key,
                records,
                ttl=ttl
            )

            # Step 11: Log successful download.
            logger.info(
                "Market history downloaded successfully",
                extra={
                    "event": "market_history_download_success",
                    "symbol": symbol,
                    "period": period if start is None else None,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "interval": interval,
                    "records_count": len(records),
                    "cache_status": "MISS"
                }
            )

            # Step 12: Return the downloaded records.
            return records

        except Exception:

            # Log the complete exception traceback.
            logger.exception(
                "Failed to download market history",
                extra={
                    "event": "market_history_download_failed",
                    "symbol": symbol,
                    "period": period if start is None else None,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "interval": interval
                }
            )

            # Inform the calling service that the download failed.
            raise RuntimeError(
                f"Failed to download market history for {symbol}"
            ) from None

    def save_history(
        self,
        db: Session,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> int:
        """
        Download historical market data and save it to PostgreSQL.

        Execution Steps:
            1. Validate and normalize the stock symbol.
            2. Download historical market data.
            3. Check whether each candle already exists in the database.
            4. Convert downloaded records into MarketData objects.
            5. Insert only new records.
            6. Commit the transaction.
            7. Roll back the transaction if database operations fail.

        Args:
            db: Active SQLAlchemy database session.
            symbol: Stock symbol to download.
            period: Historical data period (default: 1y).
            interval: Candle interval (default: 1d).

        Returns:
            Number of newly inserted records.

        Raises:
            ValueError: If the symbol is empty.
            RuntimeError: If downloading or database operations fail.
        """

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Stock symbol cannot be empty.")

        logger.info(
            "Starting historical market data save.",
            extra={
                "event": "save_history_started",
                "symbol": normalized_symbol,
                "period": period,
                "interval": interval
            }
        )

        try:
            # Step 1: Download historical market data.
            records = self.download_history(
                normalized_symbol,
                period,
                interval
            )

            if not records:
                logger.warning(
                    "No historical market data received.",
                    extra={
                        "event": "save_history_empty",
                        "symbol": normalized_symbol
                    }
                )
                return 0

            # Step 2: Track newly inserted records.
            count = 0

            for row in records:

                # Step 3: Extract the candle date.
                candle_date = row.get("Date")

                if hasattr(candle_date, "date"):
                    candle_date = candle_date.date()
                elif isinstance(candle_date, str):
                    candle_date = date.fromisoformat(candle_date[:10])

                # Step 4: Check whether this candle already exists.
                existing_record = (
                    db.query(MarketData)
                    .filter(
                        MarketData.symbol == normalized_symbol,
                        MarketData.date == candle_date
                    )
                    .first()
                )

                if existing_record:
                    continue

                # Step 5: Create a new database record.
                record = MarketData(
                    symbol=normalized_symbol,
                    date=candle_date,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"])
                )

                db.add(record)
                count += 1

            # Step 6: Commit all newly inserted records.
            db.commit()

            logger.info(
                "Historical market data saved successfully.",
                extra={
                    "event": "save_history_completed",
                    "symbol": normalized_symbol,
                    "records_count": count
                }
            )

            return count

        except (SQLAlchemyError, KeyError, TypeError, ValueError) as exc:

            # Step 7: Roll back all pending database changes.
            db.rollback()

            logger.exception(
                "Failed to save historical market data.",
                extra={
                    "event": "save_history_failed",
                    "symbol": normalized_symbol,
                    "period": period,
                    "interval": interval
                }
            )

            raise RuntimeError(
                f"Failed to save historical data for {normalized_symbol}."
            ) from exc

        except Exception as exc:

            db.rollback()

            logger.exception(
                "Unexpected error while saving historical market data.",
                extra={
                    "event": "save_history_unexpected_error",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Unexpected error saving history for {normalized_symbol}."
            ) from exc
    
    
    def get_all_data(
        self,
        db: Session
    ) -> list[MarketData]:
        """
        Retrieve all historical market data from PostgreSQL.

        Execution Steps:
            1. Log the database retrieval request.
            2. Query all MarketData records.
            3. Log the number of records retrieved.
            4. Return the database records.

        Args:
            db: Active SQLAlchemy database session.

        Returns:
            List of all MarketData records.

        Raises:
            RuntimeError: If the database query fails.
        """

        logger.info(
            "Retrieving all historical market data.",
            extra={
                "event": "get_all_data_started"
            }
        )

        try:
            # Step 1: Retrieve all market data records.
            records = db.query(MarketData).all()

            # Step 2: Log the retrieval result.
            logger.info(
                "Historical market data retrieved successfully.",
                extra={
                    "event": "get_all_data_completed",
                    "records_count": len(records)
                }
            )

            return records

        except SQLAlchemyError as exc:

            logger.exception(
                "Database error while retrieving market data.",
                extra={
                    "event": "get_all_data_failed"
                }
            )

            raise RuntimeError(
                "Failed to retrieve historical market data."
            ) from exc

    
    def get_symbol_data(
        self,
        db: Session,
        symbol: str
    ) -> list[MarketData]:
        """
        Retrieve historical market data for a specific stock symbol.

        Execution Steps:
            1. Validate and normalize the stock symbol.
            2. Query PostgreSQL for the requested symbol.
            3. Sort records by date in ascending order.
            4. Log the number of records retrieved.
            5. Return the market data records.

        Args:
            db: Active SQLAlchemy database session.
            symbol: Stock symbol to retrieve.

        Returns:
            List of MarketData records ordered by date.

        Raises:
            ValueError: If the stock symbol is empty.
            RuntimeError: If the database query fails.
        """

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Stock symbol cannot be empty.")

        logger.info(
            "Retrieving market data for symbol.",
            extra={
                "event": "get_symbol_data_started",
                "symbol": normalized_symbol
            }
        )

        try:
            # Step 1: Retrieve records for the requested symbol.
            records = (
                db.query(MarketData)
                .filter(MarketData.symbol == normalized_symbol)
                .order_by(MarketData.date.asc())
                .all()
            )

            # Step 2: Log the retrieval result.
            logger.info(
                "Symbol market data retrieved successfully.",
                extra={
                    "event": "get_symbol_data_completed",
                    "symbol": normalized_symbol,
                    "records_count": len(records)
                }
            )

            return records

        except SQLAlchemyError as exc:

            logger.exception(
                "Database error while retrieving symbol market data.",
                extra={
                    "event": "get_symbol_data_failed",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Failed to retrieve market data for {normalized_symbol}."
            ) from exc
    
    
    def get_symbol_dataframe(
        self,
        db: Session,
        symbol: str
    ) -> pd.DataFrame:
        """
        Retrieve historical market data and calculate the long-term moving average.

        Execution Steps:
            1. Validate and normalize the stock symbol.
            2. Retrieve historical records from PostgreSQL.
            3. Return an empty DataFrame if no records exist.
            4. Convert database records into a Pandas DataFrame.
            5. Calculate the configured long-term moving average.
            6. Remove rows where the moving average is unavailable.
            7. Log the final DataFrame details and return it.

        Args:
            db: Active SQLAlchemy database session.
            symbol: Stock symbol to retrieve.

        Returns:
            DataFrame containing Date, Open, High, Low, Close,
            Volume and the configured moving average.

        Raises:
            ValueError: If the stock symbol or MA period is invalid.
            RuntimeError: If database retrieval or DataFrame processing fails.
        """

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Stock symbol cannot be empty.")

        ma_period = self.config.long_ma_period

        if not isinstance(ma_period, int) or ma_period <= 0:
            raise ValueError("Long moving average period must be a positive integer.")

        logger.info(
            "Building symbol DataFrame.",
            extra={
                "event": "get_symbol_dataframe_started",
                "symbol": normalized_symbol
            }
        )

        try:
            # Step 1: Retrieve historical records from PostgreSQL.
            rows = (
                db.query(MarketData)
                .filter(MarketData.symbol == normalized_symbol)
                .order_by(MarketData.date.asc())
                .all()
            )

            # Step 2: Handle missing historical data.
            if not rows:
                logger.warning(
                    "No market data available for DataFrame generation.",
                    extra={
                        "event": "get_symbol_dataframe_empty",
                        "symbol": normalized_symbol
                    }
                )

                return pd.DataFrame()

            # Step 3: Convert database records into a DataFrame.
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

            # Step 4: Calculate the configured long-term moving average.
            ma_column = f"MA{ma_period}"

            df[ma_column] = (
                df["Close"]
                .rolling(window=ma_period)
                .mean()
            )

            # Step 5: Remove rows without a valid moving average.
            df = df.dropna(subset=[ma_column]).reset_index(drop=True)

            # Step 6: Log the final DataFrame details.
            logger.info(
                "Symbol DataFrame generated successfully.",
                extra={
                    "event": "get_symbol_dataframe_completed",
                    "symbol": normalized_symbol,
                    "records_count": len(rows),
                    "valid_records_count": len(df),
                    "ma_period": ma_period
                }
            )

            return df

        except SQLAlchemyError as exc:

            logger.exception(
                "Database error while building symbol DataFrame.",
                extra={
                    "event": "get_symbol_dataframe_db_failed",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Failed to retrieve market data for {normalized_symbol}."
            ) from exc

        except Exception as exc:

            logger.exception(
                "Unexpected error while building symbol DataFrame.",
                extra={
                    "event": "get_symbol_dataframe_failed",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Failed to build DataFrame for {normalized_symbol}."
            ) from exc
    
    
    def delete_symbol(
        self,
        db: Session,
        symbol: str
    ) -> int:
        """
        Delete all historical market data for a specific stock symbol.

        Execution Steps:
            1. Validate and normalize the stock symbol.
            2. Find and delete all matching market data records.
            3. Commit the database transaction.
            4. Log the number of deleted records.
            5. Roll back the transaction if deletion fails.

        Args:
            db: Active SQLAlchemy database session.
            symbol: Stock symbol whose historical data must be deleted.

        Returns:
            Number of deleted records.

        Raises:
            ValueError: If the stock symbol is empty.
            RuntimeError: If the database deletion fails.
        """

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Stock symbol cannot be empty.")

        logger.info(
            "Starting market data deletion.",
            extra={
                "event": "delete_symbol_started",
                "symbol": normalized_symbol
            }
        )

        try:
            # Step 1: Delete all records belonging to the symbol.
            deleted = (
                db.query(MarketData)
                .filter(MarketData.symbol == normalized_symbol)
                .delete(synchronize_session=False)
            )

            # Step 2: Commit the deletion.
            db.commit()

            logger.info(
                "Market data deletion completed.",
                extra={
                    "event": "delete_symbol_completed",
                    "symbol": normalized_symbol,
                    "records_count": deleted
                }
            )

            return deleted

        except SQLAlchemyError as exc:

            # Step 3: Roll back if the database operation fails.
            db.rollback()

            logger.exception(
                "Failed to delete symbol market data.",
                extra={
                    "event": "delete_symbol_failed",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Failed to delete market data for {normalized_symbol}."
            ) from exc

    
    def statistics(
        self,
        db: Session
    ) -> dict[str, int]:
        """
        Retrieve market database statistics.

        Execution Steps:
            1. Count all historical market data records.
            2. Count the number of distinct stock symbols.
            3. Log the calculated statistics.
            4. Return the statistics dictionary.

        Args:
            db: Active SQLAlchemy database session.

        Returns:
            Dictionary containing total_rows and symbols.

        Raises:
            RuntimeError: If the database statistics query fails.
        """

        logger.info(
            "Starting market database statistics retrieval.",
            extra={
                "event": "statistics_started"
            }
        )

        try:
            # Step 1: Count all historical market data records.
            total_rows = db.query(MarketData).count()

            # Step 2: Count distinct stock symbols.
            symbols = (
                db.query(MarketData.symbol)
                .distinct()
                .count()
            )

            # Step 3: Prepare the statistics response.
            result = {
                "total_rows": total_rows,
                "symbols": symbols
            }

            logger.info(
                "Market database statistics retrieved successfully.",
                extra={
                    "event": "statistics_completed",
                    "records_count": total_rows,
                    "symbols_count": symbols
                }
            )

            return result

        except SQLAlchemyError as exc:

            logger.exception(
                "Failed to retrieve market database statistics.",
                extra={
                    "event": "statistics_failed"
                }
            )

            raise RuntimeError(
                "Failed to retrieve market database statistics."
            ) from exc
    
    
    def load_history(
        self,
        db: Session,
        symbols: list[str],
        years: int = 5
    ) -> dict:
        """
        Load historical market data for the supplied stock symbols.

        Execution Steps:
            1. Validate the supplied stock symbols.
            2. Validate the historical data period.
            3. Log the history loading request.
            4. Delegate historical data loading to load_nifty200_history().
            5. Log the loading result.
            6. Return the original loading result.

        Args:
            db: Active SQLAlchemy database session.
            symbols: List of stock symbols to process.
            years: Number of historical years to load.

        Returns:
            The result returned by load_nifty200_history().

        Raises:
            ValueError: If symbols are empty or years is invalid.
            RuntimeError: If historical data loading fails.
        """

        # Step 1: Validate input parameters.
        if not symbols:
            raise ValueError("At least one stock symbol is required.")

        if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
            raise ValueError("Years must be a positive integer.")

        normalized_symbols = [
            symbol.strip().upper()
            for symbol in symbols
            if isinstance(symbol, str) and symbol.strip()
        ]

        if not normalized_symbols:
            raise ValueError("No valid stock symbols provided.")

        logger.info(
            "Starting historical market data loading.",
            extra={
                "event": "load_history_started",
                "symbols_count": len(normalized_symbols),
                "period": f"{years}y"
            }
        )

        try:
            # Step 2: Delegate the actual loading process.
            result = self.load_nifty200_history(
                db,
                normalized_symbols,
                years
            )

            # Step 3: Log successful completion.
            logger.info(
                "Historical market data loading completed.",
                extra={
                    "event": "load_history_completed",
                    "symbols_count": len(normalized_symbols),
                    "period": f"{years}y"
                }
            )

            return result

        except Exception as exc:

            logger.exception(
                "Historical market data loading failed.",
                extra={
                    "event": "load_history_failed",
                    "symbols_count": len(normalized_symbols),
                    "period": f"{years}y"
                }
            )

            raise RuntimeError(
                "Failed to load historical market data."
            ) from exc
    
    def _prepare_history_dataframe(
        self,
        history: pd.DataFrame | list[dict]
    ) -> pd.DataFrame:
        """
        Normalize downloaded historical data into a Pandas DataFrame.

        Execution Steps:
            1. Convert list-based historical data into a DataFrame.
            2. Move the Date column into the DataFrame index when available.
            3. Convert the index into datetime values.
            4. Normalize timezone-aware dates to Asia/Kolkata.
            5. Remove invalid dates.
            6. Exclude the current trading day's incomplete candle
            until 4:00 PM IST.
            7. Return the normalized DataFrame.

        Args:
            history: Downloaded historical data as a DataFrame or list.

        Returns:
            Normalized DataFrame with a timezone-naive datetime index.
        """

        if isinstance(history, pd.DataFrame):
            df = history.copy()
        else:
            df = pd.DataFrame(history)

        if df.empty:
            return df

        # Use the Date column as the index when available.
        if "Date" in df.columns:
            df = df.set_index("Date")

        # Convert index to datetime.
        df.index = pd.to_datetime(df.index, errors="coerce")

        # Remove invalid dates.
        df = df[~df.index.isna()]

        if df.empty:
            return df

        # Normalize timezone-aware timestamps to Indian Standard Time.
        if df.index.tz is not None:
            df.index = (
                df.index
                .tz_convert("Asia/Kolkata")
                .tz_localize(None)
            )

        # Exclude today's incomplete candle before 4 PM IST.
        india_now = datetime.now(
            ZoneInfo("Asia/Kolkata")
        )

        if india_now.time() < time(16, 0):
            today = pd.Timestamp(india_now.date())

            df = df[df.index.normalize() < today]

        return df
        
    
    def load_nifty200_history(
        self,
        db: Session,
        symbols: list[str],
        years: int = 5
    ) -> dict[str, int]:
        """
        Load initial historical data or incrementally update market data.

        New symbols receive the configured historical period.
        Existing symbols download only from their latest database
        date through the current date.

        Weekend and future-dated records are rejected.
        The latest stored candle is downloaded again to allow corrections.
        """

        if not symbols:
            raise ValueError("At least one stock symbol is required.")

        if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
            raise ValueError("Years must be a positive integer.")

        normalized_symbols = list(dict.fromkeys(
            symbol.strip().upper()
            for symbol in symbols
            if isinstance(symbol, str) and symbol.strip()
        ))

        if not normalized_symbols:
            raise ValueError("No valid stock symbols provided.")

        processed = 0
        inserted = 0
        updated = 0
        failed = 0
        rejected_records = 0

        total_symbols = len(normalized_symbols)

        today = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).date()

        end_date = today + timedelta(days=1)

        logger.info(
            "Starting incremental NIFTY 200 market data loading.",
            extra={
                "event": "load_nifty200_started",
                "symbols_count": total_symbols,
                "historical_years": years,
                "end_date": end_date.isoformat()
            }
        )

        for symbol in normalized_symbols:

            processed += 1

            symbol_inserted = 0
            symbol_updated = 0

            try:
                # Step 1: Find the latest available database date.
                # Step 1: Find the latest valid trading date in the database.
                latest_date = (
                    db.query(func.max(MarketData.date))
                    .filter(
                        MarketData.symbol == symbol,
                        func.extract("isodow", MarketData.date).between(1, 5),
                        MarketData.date <= today
                    )
                    .scalar()
                )

                # Step 2: Download initial or incremental history.
                if latest_date is None:

                    history = self.download_history(
                        symbol=symbol,
                        period=f"{years}y",
                        interval="1d"
                    )

                else:

                    history = self.download_history(
                        symbol=symbol,
                        start=latest_date,
                        end=end_date,
                        interval="1d"
                    )

                # Step 3: Normalize downloaded market data.
                df = self._prepare_history_dataframe(history)

                if df.empty:
                    logger.warning(
                        "No historical data received for symbol.",
                        extra={
                            "event": "load_nifty200_empty",
                            "symbol": symbol
                        }
                    )
                    continue

                # Step 4: Reject weekends and future-dated records.
                valid_mask = [
                    timestamp.dayofweek < 5
                    and timestamp.date() <= today
                    for timestamp in df.index
                ]

                rejected_dates = [
                    timestamp.isoformat()
                    for timestamp, is_valid in zip(df.index, valid_mask)
                    if not is_valid
                ]

                rejected_records += len(rejected_dates)

                if rejected_dates:
                    logger.warning(
                        "Rejected invalid market data dates.",
                        extra={
                            "event": "load_nifty200_invalid_dates",
                            "symbol": symbol,
                            "rejected_dates": rejected_dates
                        }
                    )

                df = df.loc[valid_mask].copy()

                if df.empty:
                    continue

                # Step 5: Convert downloaded dates into Python dates.
                trade_dates = [
                    pd.Timestamp(index).date()
                    for index in df.index
                ]

                # Step 6: Retrieve existing records in one query.
                existing_records = (
                    db.query(MarketData)
                    .filter(
                        MarketData.symbol == symbol,
                        MarketData.date.in_(trade_dates)
                    )
                    .all()
                )

                existing_map = {
                    record.date: record
                    for record in existing_records
                }

                # Step 7: Insert missing candles or update existing candles.
                for index, row in df.iterrows():

                    trade_date = pd.Timestamp(index).date()

                    existing = existing_map.get(trade_date)

                    if existing:

                        existing.open = float(row["Open"])
                        existing.high = float(row["High"])
                        existing.low = float(row["Low"])
                        existing.close = float(row["Close"])
                        existing.volume = float(row["Volume"])

                        symbol_updated += 1

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

                        symbol_inserted += 1

                # Step 8: Commit this symbol's transaction.
                db.commit()

                inserted += symbol_inserted
                updated += symbol_updated

                logger.info(
                    "Stock market data processed successfully.",
                    extra={
                        "event": "load_nifty200_symbol_completed",
                        "symbol": symbol,
                        "records_inserted": symbol_inserted,
                        "records_updated": symbol_updated
                    }
                )

            except Exception:

                db.rollback()
                failed += 1

                logger.exception(
                    "Failed to load market data for stock.",
                    extra={
                        "event": "load_nifty200_symbol_failed",
                        "symbol": symbol
                    }
                )

        result = {
            "symbols": total_symbols,
            "processed": processed,
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "rejected_records": rejected_records
        }

        logger.info(
            "NIFTY 200 incremental market data loading completed.",
            extra={
                "event": "load_nifty200_completed",
                "symbols_count": total_symbols,
                "records_inserted": inserted,
                "records_updated": updated,
                "rejected_records": rejected_records,
                "failed_symbols": failed
            }
        )

        return result

    
    def clear_market_data(
        self,
        db: Session
    ) -> dict[str, int | str]:
        """
        Delete all historical market data from PostgreSQL.

        Execution Steps:
            1. Count the existing market data records.
            2. Log the destructive database operation.
            3. Delete all market data records.
            4. Commit the deletion.
            5. Log the number of deleted records.
            6. Return the deletion summary.

        Args:
            db: Active SQLAlchemy database session.

        Returns:
            Dictionary containing the deletion message and row count.

        Raises:
            RuntimeError: If the database deletion fails.
        """

        logger.warning(
            "Starting complete market data deletion.",
            extra={
                "event": "clear_market_data_started"
            }
        )

        try:
            # Step 1: Count records before deletion.
            count_before = db.query(MarketData).count()

            logger.info(
                "Market data records before deletion.",
                extra={
                    "event": "clear_market_data_before",
                    "records_count": count_before
                }
            )

            # Step 2: Delete all market data records once.
            deleted = (
                db.query(MarketData)
                .delete(synchronize_session=False)
            )

            # Step 3: Commit the deletion.
            db.commit()

            # Step 4: Verify the remaining record count.
            count_after = db.query(MarketData).count()

            logger.warning(
                "Market data deletion completed.",
                extra={
                    "event": "clear_market_data_completed",
                    "records_deleted": deleted,
                    "records_remaining": count_after
                }
            )

            return {
                "message": "Market data cleared successfully",
                "rows_deleted": deleted
            }

        except SQLAlchemyError as exc:

            db.rollback()

            logger.exception(
                "Failed to clear market data.",
                extra={
                    "event": "clear_market_data_failed"
                }
            )

            raise RuntimeError(
                "Failed to clear market data."
            ) from exc
    
    
    def get_market_context_data(self) -> pd.DataFrame:
        """
        Download NIFTY 50 market context data and calculate its long-term MA.

        Execution Steps:
            1. Download one year of NIFTY 50 historical data.
            2. Normalize the downloaded data into a DataFrame.
            3. Return an empty DataFrame if no data is available.
            4. Calculate the configured long-term moving average.
            5. Remove rows without valid moving average values.
            6. Log the final DataFrame details.
            7. Return the market context DataFrame.

        Returns:
            DataFrame containing NIFTY 50 OHLCV data and its long-term MA.

        Raises:
            RuntimeError: If downloading or processing market data fails.
        """

        logger.info(
            "Starting NIFTY 50 market context retrieval.",
            extra={
                "event": "market_context_started",
                "symbol": "^NSEI",
                "period": "1y"
            }
        )

        try:
            # Step 1: Download NIFTY 50 historical data.
            history = self.download_history(
                symbol="^NSEI",
                period="1y"
            )

            # Step 2: Normalize the downloaded data.
            df = self._prepare_history_dataframe(history)

            if df.empty:
                logger.warning(
                    "No NIFTY 50 market context data available.",
                    extra={
                        "event": "market_context_empty",
                        "symbol": "^NSEI"
                    }
                )

                return df

            # Step 3: Calculate the configured long-term moving average.
            ma_period = self.config.long_ma_period

            if not isinstance(ma_period, int) or ma_period <= 0:
                raise ValueError(
                    "Long moving average period must be a positive integer."
                )

            ma_column = f"MA{ma_period}"

            df[ma_column] = (
                df["Close"]
                .rolling(window=ma_period)
                .mean()
            )

            # Step 4: Remove rows without valid moving average values.
            df = df.dropna()

            logger.info(
                "NIFTY 50 market context generated successfully.",
                extra={
                    "event": "market_context_completed",
                    "symbol": "^NSEI",
                    "ma_period": ma_period,
                    "records_count": len(df)
                }
            )

            return df

        except Exception as exc:

            logger.exception(
                "Failed to generate NIFTY 50 market context.",
                extra={
                    "event": "market_context_failed",
                    "symbol": "^NSEI"
                }
            )

            raise RuntimeError(
                "Failed to retrieve NIFTY 50 market context data."
            ) from exc
        

    def _load_index_history_incremental(
        self,
        db: Session,
        symbol: str,
        yahoo_symbol: str,
        years: int
    ) -> dict[str, int | str]:
        """Load full history once, then update only recent history."""

        if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
            raise ValueError("Years must be a positive integer.")

        try:
            # 1. Find the latest valid stored trading date.
            latest_date = (
                db.query(func.max(MarketData.date))
                .filter(
                    MarketData.symbol == symbol,
                    func.extract("isodow", MarketData.date).between(1, 5)
                )
                .scalar()
            )

            # 2. Full download for new symbols; incremental download otherwise.
            period = f"{years}y" if latest_date is None else "1mo"

            logger.info(
                "Starting incremental index history loading.",
                extra={
                    "event": "index_history_started",
                    "symbol": symbol,
                    "yahoo_symbol": yahoo_symbol,
                    "latest_date": str(latest_date),
                    "period": period
                }
            )

            # 3. Download history using the existing Redis-enabled method.
            history = self.download_history(
                symbol=yahoo_symbol,
                period=period
            )

            df = self._prepare_history_dataframe(history)

            if df.empty:
                return {
                    "symbol": symbol,
                    "inserted": 0,
                    "updated": 0,
                    "total_rows": 0,
                    "status": "NO_DATA"
                }

            # 4. Keep weekdays only and reject future dates.
            today = datetime.now(
                __import__("zoneinfo").ZoneInfo("Asia/Kolkata")
            ).date()

            valid_rows = []

            for index, row in df.iterrows():
                trade_date = pd.Timestamp(index).date()

                if trade_date.weekday() >= 5 or trade_date > today:
                    continue

                valid_rows.append((trade_date, row))

            if not valid_rows:
                return {
                    "symbol": symbol,
                    "inserted": 0,
                    "updated": 0,
                    "total_rows": 0,
                    "status": "NO_VALID_DATA"
                }

            # 5. Fetch existing records for downloaded dates.
            trade_dates = [trade_date for trade_date, _ in valid_rows]

            existing_records = (
                db.query(MarketData)
                .filter(
                    MarketData.symbol == symbol,
                    MarketData.date.in_(trade_dates)
                )
                .all()
            )

            existing_map = {
                record.date: record
                for record in existing_records
            }

            inserted = 0
            updated = 0

            # 6. Insert missing candles and update existing candles.
            for trade_date, row in valid_rows:
                existing = existing_map.get(trade_date)

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

            # 7. Commit database changes.
            db.commit()

            result = {
                "symbol": symbol,
                "inserted": inserted,
                "updated": updated,
                "total_rows": len(valid_rows),
                "status": "SUCCESS"
            }

            logger.info(
                "Incremental index history loading completed.",
                extra={
                    "event": "index_history_completed",
                    **result
                }
            )

            return result

        except Exception:
            db.rollback()

            logger.exception(
                "Incremental index history loading failed.",
                extra={
                    "event": "index_history_failed",
                    "symbol": symbol
                }
            )

            raise

    
    def load_nifty_index_history(
        self,
        db: Session,
        years: int = 7
    ) -> dict[str, int | str]:
        """Load or incrementally update NIFTY 50 history."""

        return self._load_index_history_incremental(
            db=db,
            symbol="NIFTY50",
            yahoo_symbol="^NSEI",
            years=years
        )

    
    def get_nifty_history(
        self,
        db: Session,
        signal_date: date
    ) -> pd.DataFrame:
        """
        Retrieve NIFTY 50 historical data up to a specified signal date.

        Execution Steps:
            1. Query NIFTY50 records from PostgreSQL.
            2. Filter records up to the signal date.
            3. Sort records chronologically.
            4. Convert database records into a DataFrame.
            5. Return the DataFrame.

        Args:
            db: Active SQLAlchemy database session.
            signal_date: Latest date allowed in the returned history.

        Returns:
            DataFrame containing Date, Open, High, Low, Close and Volume.

        Raises:
            RuntimeError: If the database query or DataFrame creation fails.
        """

        logger.info(
            "Retrieving NIFTY 50 historical data.",
            extra={
                "event": "get_nifty_history_started",
                "symbol": "NIFTY50",
                "signal_date": str(signal_date)
            }
        )

        try:
            # Step 1: Retrieve NIFTY 50 records up to the signal date.
            rows = (
                db.query(MarketData)
                .filter(
                    MarketData.symbol == "NIFTY50",
                    MarketData.date <= signal_date
                )
                .order_by(MarketData.date.asc())
                .all()
            )

            if not rows:
                logger.warning(
                    "No NIFTY 50 history found for the requested date.",
                    extra={
                        "event": "get_nifty_history_empty",
                        "signal_date": str(signal_date)
                    }
                )

                return pd.DataFrame()

            # Step 2: Convert database records into a DataFrame.
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

            logger.info(
                "NIFTY 50 historical data retrieved successfully.",
                extra={
                    "event": "get_nifty_history_completed",
                    "records_count": len(df),
                    "signal_date": str(signal_date)
                }
            )

            return df

        except SQLAlchemyError as exc:

            logger.exception(
                "Database error retrieving NIFTY 50 history.",
                extra={
                    "event": "get_nifty_history_failed"
                }
            )

            raise RuntimeError(
                "Failed to retrieve NIFTY 50 historical data."
            ) from exc

        except Exception as exc:

            logger.exception(
                "Unexpected error processing NIFTY 50 history.",
                extra={
                    "event": "get_nifty_history_processing_failed"
                }
            )

            raise RuntimeError(
                "Failed to process NIFTY 50 historical data."
            ) from exc
    
    
    def prepare_nifty_context(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate NIFTY 50 market context indicators.

        Execution Steps:
            1. Check whether historical data is available.
            2. Validate the configured indicator periods.
            3. Create a copy of the input DataFrame.
            4. Calculate the long-term moving average.
            5. Calculate the momentum moving average.
            6. Calculate percentage momentum.
            7. Calculate True Range and Average True Range.
            8. Calculate ATR percentage.
            9. Remove rows containing unavailable indicator values.
            10. Return the prepared market context DataFrame.

        Args:
            df: Historical NIFTY 50 OHLCV DataFrame.

        Returns:
            DataFrame containing the original market data and
            calculated MA, Momentum, ATR and ATRPercent columns.

        Raises:
            ValueError: If required columns or indicator periods are invalid.
            RuntimeError: If indicator calculations fail.
        """

        if df.empty:
            logger.warning(
                "Cannot prepare NIFTY context because input data is empty.",
                extra={
                    "event": "prepare_nifty_context_empty"
                }
            )
            return df

        required_columns = {"Close", "High", "Low"}

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required market data columns: {sorted(missing_columns)}"
            )

        # Step 1: Retrieve configured indicator periods.
        ma_period = self.config.long_ma_period
        momentum_period = self.config.momentum_period
        atr_period = self.config.atr_period

        periods = {
            "long_ma_period": ma_period,
            "momentum_period": momentum_period,
            "atr_period": atr_period
        }

        # Step 2: Validate all indicator periods.
        for name, period in periods.items():
            if (
                not isinstance(period, int)
                or isinstance(period, bool)
                or period <= 0
            ):
                raise ValueError(
                    f"{name} must be a positive integer."
                )

        logger.info(
            "Starting NIFTY market context calculations.",
            extra={
                "event": "prepare_nifty_context_started",
                "records_count": len(df),
                "ma_period": ma_period,
                "momentum_period": momentum_period,
                "atr_period": atr_period
            }
        )

        try:
            # Step 3: Copy input data to avoid modifying the original DataFrame.
            df = df.copy()

            # Step 4: Calculate long-term moving average.
            df[f"MA{ma_period}"] = (
                df["Close"]
                .rolling(ma_period)
                .mean()
            )

            # Step 5: Calculate momentum moving average.
            df[f"MA{momentum_period}"] = (
                df["Close"]
                .rolling(momentum_period)
                .mean()
            )

            # Step 6: Calculate percentage momentum.
            df[f"Momentum{momentum_period}"] = (
                (
                    df["Close"]
                    - df["Close"].shift(momentum_period)
                )
                / df["Close"].shift(momentum_period)
            ) * 100

            # Step 7: Calculate True Range.
            tr = pd.concat([
                df["High"] - df["Low"],
                (df["High"] - df["Close"].shift()).abs(),
                (df["Low"] - df["Close"].shift()).abs()
            ], axis=1).max(axis=1)

            # Step 8: Calculate Average True Range.
            df[f"ATR{atr_period}"] = (
                tr.rolling(atr_period).mean()
            )

            # Step 9: Calculate ATR percentage.
            df["ATRPercent"] = (
                df[f"ATR{atr_period}"] / df["Close"]
            ) * 100

            # Step 10: Remove rows with unavailable indicator values.
            df = df.dropna()

            logger.info(
                "NIFTY market context calculations completed.",
                extra={
                    "event": "prepare_nifty_context_completed",
                    "records_count": len(df),
                    "ma_period": ma_period,
                    "momentum_period": momentum_period,
                    "atr_period": atr_period
                }
            )

            return df

        except Exception as exc:

            logger.exception(
                "Failed to calculate NIFTY market context indicators.",
                extra={
                    "event": "prepare_nifty_context_failed"
                }
            )

            raise RuntimeError(
                "Failed to prepare NIFTY market context."
            ) from exc

    
    def load_sector_history(
        self,
        db: Session,
        sector: Sector,
        years: int = 7
    ) -> dict[str, int | str]:
        """Load or incrementally update sector index history."""

        try:
            yahoo_symbol = SECTOR_INDEX_SYMBOLS[sector]
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"Invalid or unsupported sector: {sector}"
            ) from exc

        return self._load_index_history_incremental(
            db=db,
            symbol=sector.value,
            yahoo_symbol=yahoo_symbol,
            years=years
        )

    
    def load_daily_market_data(
        self,
        db: Session,
        symbols: list[str],
        stock_years: int = 5,
        index_years: int = 7,
        sector_years: int = 7
    ) -> dict:
        """
        Orchestrate daily loading of all market reference and price data.

        Execution order:
            1. Update stock master.
            2. Update NIFTY 200 historical data.
            3. Update NIFTY 50 historical data.
            4. Update all configured sector historical data.

        Existing loader methods handle initial and incremental downloads.
        """

        if not symbols:
            raise ValueError("NIFTY 200 symbols cannot be empty.")

        results = {
            "status": "IN_PROGRESS",
            "stock_master": None,
            "nifty200": None,
            "nifty50": None,
            "sectors": {}
        }

        logger.info(
            "Daily market data orchestration started.",
            extra={
                "event": "daily_market_data_started",
                "symbols_count": len(symbols)
            }
        )

        try:
            # Step 1: Update stock master.
            logger.info(
                "Step 1: Loading stock master.",
                extra={"event": "daily_market_stock_master_started"}
            )

            results["stock_master"] = self.load_stock_master(
                db=db,
                symbols=symbols
            )

            # Step 2: Update NIFTY 200 historical data.
            logger.info(
                "Step 2: Loading NIFTY 200 history.",
                extra={"event": "daily_market_nifty200_started"}
            )

            results["nifty200"] = self.load_nifty200_history(
                db=db,
                symbols=symbols,
                years=stock_years
            )

            if results["nifty200"]["failed"] > 0:
                raise RuntimeError(
                    "NIFTY 200 history loading failed for one or more symbols."
                )

            # Step 3: Update NIFTY 50 history.
            logger.info(
                "Step 3: Loading NIFTY 50 history.",
                extra={"event": "daily_market_nifty50_started"}
            )

            results["nifty50"] = self.load_nifty_index_history(
                db=db,
                years=index_years
            )

            if results["nifty50"].get("status") != "SUCCESS":
                raise RuntimeError(
                    "NIFTY 50 history loading was unsuccessful."
                )

            # Step 4: Update all configured sector histories.
            logger.info(
                "Step 4: Loading sector histories.",
                extra={"event": "daily_market_sectors_started"}
            )

            
            for sector in SECTOR_INDEX_SYMBOLS:
                sector_result = self.load_sector_history(
                    db=db,
                    sector=sector,
                    years=sector_years,
                )

                results["sectors"][sector.value] = sector_result

                # Support both original and incremental loader responses.
                sector_status = sector_result.get("status")

                if sector_status is not None:
                    success = sector_status == "SUCCESS"
                else:
                    success = sector_result.get("total_rows", 0) > 0

                if not success:
                    raise RuntimeError(
                        f"Sector history loading failed: {sector.value}. "
                        f"Yahoo symbol: {SECTOR_INDEX_SYMBOLS[sector]}. "
                        f"Loader result: {sector_result}"
                    )


            # All loading operations completed.
            results["status"] = "SUCCESS"

            logger.info(
                "Daily market data orchestration completed.",
                extra={
                    "event": "daily_market_data_completed",
                    "status": results["status"]
                }
            )

            return results

        except Exception as exc:
            results["status"] = "FAILED"
            results["error"] = str(exc)

            logger.exception(
                "Daily market data orchestration failed.",
                extra={
                    "event": "daily_market_data_failed"
                }
            )

            raise
    
    def get_market_history(
        self,
        db: Session,
        symbol: str,
        end_date: date
    ) -> pd.DataFrame:
        """
        Retrieve historical market data for a symbol up to an end date.

        Execution Steps:
            1. Validate and normalize the stock symbol.
            2. Query PostgreSQL for matching market records.
            3. Filter records up to the specified end date.
            4. Sort records chronologically.
            5. Convert database records into a DataFrame.
            6. Return the historical DataFrame.

        Args:
            db: Active SQLAlchemy database session.
            symbol: Stock, index or sector symbol.
            end_date: Latest date allowed in the returned history.

        Returns:
            DataFrame containing Date, Open, High, Low, Close and Volume.

        Raises:
            ValueError: If the symbol is empty.
            RuntimeError: If database retrieval fails.
        """

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Market symbol cannot be empty.")

        logger.info(
            "Retrieving historical market data.",
            extra={
                "event": "get_market_history_started",
                "symbol": normalized_symbol,
                "end_date": str(end_date)
            }
        )

        try:
            # Step 1: Retrieve records up to the requested end date.
            rows = (
                db.query(MarketData)
                .filter(
                    MarketData.symbol == normalized_symbol,
                    MarketData.date <= end_date
                )
                .order_by(MarketData.date.asc())
                .all()
            )

            if not rows:
                logger.warning(
                    "No historical market records found.",
                    extra={
                        "event": "get_market_history_empty",
                        "symbol": normalized_symbol,
                        "end_date": str(end_date)
                    }
                )

                return pd.DataFrame()

            # Step 2: Convert database records into a DataFrame.
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

            # Step 3: Ensure chronological ordering.
            df = df.sort_values("Date").reset_index(drop=True)

            logger.info(
                "Historical market data retrieved successfully.",
                extra={
                    "event": "get_market_history_completed",
                    "symbol": normalized_symbol,
                    "records_count": len(df)
                }
            )

            return df

        except SQLAlchemyError as exc:

            logger.exception(
                "Database error retrieving historical market data.",
                extra={
                    "event": "get_market_history_failed",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Failed to retrieve market history for {normalized_symbol}."
            ) from exc

        except Exception as exc:

            logger.exception(
                "Unexpected error processing historical market data.",
                extra={
                    "event": "get_market_history_processing_failed",
                    "symbol": normalized_symbol
                }
            )

            raise RuntimeError(
                f"Failed to process market history for {normalized_symbol}."
            ) from exc
    
    
    def get_sector_history(
        self,
        db: Session,
        sector: Sector,
        signal_date: date
    ) -> pd.DataFrame:
        """
        Retrieve historical market data for a sector up to a signal date.

        Execution Steps:
            1. Validate the sector.
            2. Retrieve the sector database symbol.
            3. Delegate historical retrieval to get_market_history().
            4. Log the retrieval result.
            5. Return the sector historical DataFrame.

        Args:
            db: Active SQLAlchemy database session.
            sector: Sector enum identifying the sector.
            signal_date: Latest date allowed in the returned history.

        Returns:
            DataFrame containing the sector's historical OHLCV data.

        Raises:
            ValueError: If the sector is invalid.
            RuntimeError: If historical data retrieval fails.
        """

        try:
            # Step 1: Resolve the sector's database symbol.
            symbol = sector.value

            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError("Invalid sector symbol.")

        except (AttributeError, TypeError) as exc:
            raise ValueError(
                f"Invalid sector: {sector}"
            ) from exc

        logger.info(
            "Retrieving sector historical data.",
            extra={
                "event": "get_sector_history_started",
                "symbol": symbol,
                "signal_date": str(signal_date)
            }
        )

        try:
            # Step 2: Delegate retrieval to the reusable market history method.
            df = self.get_market_history(
                db=db,
                symbol=symbol,
                end_date=signal_date
            )

            logger.info(
                "Sector historical data retrieved.",
                extra={
                    "event": "get_sector_history_completed",
                    "symbol": symbol,
                    "records_count": len(df)
                }
            )

            return df

        except Exception as exc:

            logger.exception(
                "Failed to retrieve sector historical data.",
                extra={
                    "event": "get_sector_history_failed",
                    "symbol": symbol
                }
            )

            raise RuntimeError(
                f"Failed to retrieve historical data for sector {symbol}."
            ) from exc
    
    
    def load_stock_master(
        self,
        db: Session,
        symbols: list[str]
    ) -> dict:
        """
        Load stock master information from Yahoo Finance.

        Fetches company name, sector, and industry for each symbol.
        Existing stock records are updated; new records are inserted.

        Args:
            db: Active SQLAlchemy database session.
            symbols: List of Yahoo Finance stock symbols.

        Returns:
            dict: Summary containing inserted, updated, failed,
                and total stock counts.

        Raises:
            ValueError: If the symbol list is empty or invalid.
            RuntimeError: If the database transaction fails.
        """
        if not symbols:
            raise ValueError("Stock symbol list cannot be empty.")

        # Normalize symbols and remove duplicates while preserving order.
        symbols = list(dict.fromkeys(
            symbol.strip().upper()
            for symbol in symbols
            if isinstance(symbol, str) and symbol.strip()
        ))

        if not symbols:
            raise ValueError("No valid stock symbols provided.")

        inserted = 0
        updated = 0
        failed = []

        logger.info(
            "Stock master loading started",
            extra={"symbols_count": len(symbols)}
        )

        for symbol in symbols:
            logger.info(
                "Loading stock master",
                extra={"symbol": symbol}
            )

            try:
                # Step 1: Fetch company information from Yahoo Finance.
                ticker = yf.Ticker(symbol)
                info = ticker.info

                if not info:
                    raise ValueError(
                        f"No company information returned for {symbol}"
                    )

                # Step 2: Extract company details.
                company_name = info.get("longName", "")
                yahoo_sector = info.get("sector", "")
                industry = info.get("industry", "")

                # Step 3: Map Yahoo Finance sector to AthenaAI sector.
                sector = YAHOO_TO_SECTOR.get(
                    yahoo_sector,
                    Sector.UNKNOWN
                )

                # Step 4: Check whether the stock already exists.
                existing = (
                    db.query(StockMaster)
                    .filter(StockMaster.symbol == symbol)
                    .first()
                )

                if existing:
                    # Update existing stock master record.
                    existing.company_name = company_name
                    existing.sector = sector.value
                    existing.industry = industry

                    updated += 1

                    logger.info(
                        "Stock master updated",
                        extra={
                            "symbol": symbol,
                            "sector": sector.value
                        }
                    )

                else:
                    # Insert a new stock master record.
                    db.add(
                        StockMaster(
                            symbol=symbol,
                            company_name=company_name,
                            sector=sector.value,
                            industry=industry
                        )
                    )

                    inserted += 1

                    logger.info(
                        "Stock master inserted",
                        extra={
                            "symbol": symbol,
                            "sector": sector.value
                        }
                    )

            except Exception:
                failed.append(symbol)

                logger.exception(
                    "Stock master loading failed",
                    extra={"symbol": symbol}
                )

                # Roll back pending database changes before stopping.
                db.rollback()
                raise

        # Step 5: Commit all stock master changes.
        try:
            db.commit()

        except SQLAlchemyError:
            db.rollback()

            logger.exception("Stock master database commit failed")
            raise

        result = {
            "inserted": inserted,
            "updated": updated,
            "failed": len(failed),
            "total": len(symbols)
        }

        logger.info(
            "Stock master loading completed",
            extra=result
        )

        return result

    def get_latest_completed_session_date(self) -> date:
        """
        Returns the latest completed NSE trading date.

        Treats the current session as incomplete until 4 PM IST.
        """

        india_tz = ZoneInfo("Asia/Kolkata")
        now = datetime.now(india_tz)

        if now.time() < time(16, 0):
            return (now.date() - timedelta(days=1))

        return now.date()