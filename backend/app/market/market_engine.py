from datetime import date, datetime

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
        interval: str = "1d"
    ) -> list[dict]:
        """
        Download historical OHLCV data with Redis caching.

        Retrieves historical market data from Yahoo Finance.
        Redis is checked first to avoid unnecessary external
        API requests for previously downloaded data.

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

        Returns:
            list[dict]: Historical OHLCV records.

        Raises:
            ValueError: If the supplied parameters are invalid.
            RuntimeError: If Yahoo Finance download fails.

        Notes:
            Redis failures do not prevent downloading market data.
            Cached data is temporary and expires according to TTL.
        """

        # Step 1: Validate input parameters.
        if not symbol or not symbol.strip():
            raise ValueError("Stock symbol cannot be empty")

        if not period or not interval:
            raise ValueError("Period and interval are required")

        symbol = symbol.strip().upper()

        # Step 2: Generate a unique cache key.
        # Different symbols, periods and intervals must have
        # separate cache entries.
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
                    "period": period,
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
                "period": period,
                "interval": interval,
                "cache_status": "MISS"
            }
        )

        try:

            # Step 6: Initialize Yahoo Finance ticker.
            ticker = yf.Ticker(symbol)

            # Step 7: Download historical OHLCV data.
            df = ticker.history(
                period=period,
                interval=interval
            )

            # Step 8: Check whether data was returned.
            if df.empty:

                logger.warning(
                    "Yahoo Finance returned no market history",
                    extra={
                        "event": "market_history_empty",
                        "symbol": symbol,
                        "period": period,
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
                    "period": period,
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
                    "period": period,
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
            4. Return the normalized DataFrame.

        Args:
            history: Downloaded historical data as a DataFrame or list.

        Returns:
            Normalized DataFrame with a datetime index.
        """

        if isinstance(history, pd.DataFrame):
            df = history.copy()
        else:
            df = pd.DataFrame(history)

        if df.empty:
            return df

        # Use the Date column as the index when download_history returns records.
        if "Date" in df.columns:
            df = df.set_index("Date")

        # Ensure the index supports datetime operations.
        df.index = pd.to_datetime(df.index)

        return df
    
    def load_nifty200_history(
        self,
        db: Session,
        symbols: list[str],
        years: int = 5
    ) -> dict[str, int]:
        """
        Load or update historical data for multiple stock symbols.

        Execution Steps:
            1. Validate the symbols and historical period.
            2. Process each stock symbol individually.
            3. Check the latest available database date.
            4. Download five-year history for new symbols or one month
            of history for existing symbols.
            5. Normalize the downloaded data.
            6. Identify existing records and update them.
            7. Insert new records.
            8. Commit each symbol separately.
            9. Roll back failed symbols and continue processing.
            10. Return the final loading statistics.

        Args:
            db: Active SQLAlchemy database session.
            symbols: List of stock symbols to process.
            years: Historical period for new symbols.

        Returns:
            Dictionary containing symbols, processed, inserted,
            updated and failed counts.

        Raises:
            ValueError: If symbols are empty or years is invalid.
        """

        if not symbols:
            raise ValueError("At least one stock symbol is required.")

        if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
            raise ValueError("Years must be a positive integer.")

        # Normalize and remove duplicate symbols.
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

        total_symbols = len(normalized_symbols)

        logger.info(
            "Starting NIFTY 200 historical data loading.",
            extra={
                "event": "load_nifty200_started",
                "symbols_count": total_symbols,
                "period": f"{years}y"
            }
        )

        for symbol in normalized_symbols:

            processed += 1

            logger.info(
                "Processing stock historical data.",
                extra={
                    "event": "load_nifty200_symbol_started",
                    "symbol": symbol,
                    "processed": processed,
                    "symbols_count": total_symbols
                }
            )

            # Keep temporary counters until the symbol transaction commits.
            symbol_inserted = 0
            symbol_updated = 0

            try:
                # Step 1: Find the latest available database date.
                latest_date = (
                    db.query(func.max(MarketData.date))
                    .filter(MarketData.symbol == symbol)
                    .scalar()
                )

                # Step 2: Select the download period.
                period = f"{years}y" if latest_date is None else "1mo"

                # Step 3: Download historical data.
                history = self.download_history(
                    symbol=symbol,
                    period=period
                )

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

                # Step 4: Convert downloaded dates into Python dates.
                trade_dates = [
                    pd.Timestamp(index).date()
                    for index in df.index
                ]

                # Step 5: Retrieve existing records in one query.
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

                # Step 6: Insert new records or update existing records.
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

                # Step 7: Commit this symbol's transaction.
                db.commit()

                # Update global counters only after successful commit.
                inserted += symbol_inserted
                updated += symbol_updated

                logger.info(
                    "Stock historical data processed successfully.",
                    extra={
                        "event": "load_nifty200_symbol_completed",
                        "symbol": symbol,
                        "records_inserted": symbol_inserted,
                        "records_updated": symbol_updated
                    }
                )

            except Exception:

                # Roll back only the failed symbol's pending transaction.
                db.rollback()

                failed += 1

                logger.exception(
                    "Failed to load historical data for stock.",
                    extra={
                        "event": "load_nifty200_symbol_failed",
                        "symbol": symbol
                    }
                )

                continue

        # Step 8: Prepare final loading statistics.
        result = {
            "symbols": total_symbols,
            "processed": processed,
            "inserted": inserted,
            "updated": updated,
            "failed": failed
        }

        logger.info(
            "NIFTY 200 historical data loading completed.",
            extra={
                "event": "load_nifty200_completed",
                "symbols_count": total_symbols,
                "records_inserted": inserted,
                "records_updated": updated,
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
        
    
    def load_nifty_index_history(
        self,
        db: Session,
        years: int = 7
    ) -> dict[str, int | str]:
        """
        Load or update historical NIFTY 50 index data.

        Execution Steps:
            1. Validate the historical period.
            2. Download NIFTY 50 index history.
            3. Normalize the downloaded data.
            4. Retrieve existing NIFTY50 records for downloaded dates.
            5. Update existing records.
            6. Insert missing records.
            7. Commit the database transaction.
            8. Log the loading statistics.
            9. Return the loading summary.

        Args:
            db: Active SQLAlchemy database session.
            years: Number of historical years to download.

        Returns:
            Dictionary containing symbol, inserted, updated and total_rows.

        Raises:
            ValueError: If years is invalid.
            RuntimeError: If downloading or database operations fail.
        """

        if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
            raise ValueError("Years must be a positive integer.")

        symbol = "NIFTY50"

        logger.info(
            "Starting NIFTY 50 index history loading.",
            extra={
                "event": "nifty_index_history_started",
                "symbol": symbol,
                "period": f"{years}y"
            }
        )

        try:
            # Step 1: Download NIFTY 50 index history.
            history = self.download_history(
                symbol="^NSEI",
                period=f"{years}y"
            )

            # Step 2: Normalize downloaded data.
            df = self._prepare_history_dataframe(history)

            if df.empty:
                logger.warning(
                    "No NIFTY 50 index history received.",
                    extra={
                        "event": "nifty_index_history_empty",
                        "symbol": symbol
                    }
                )

                return {
                    "symbol": symbol,
                    "inserted": 0,
                    "updated": 0,
                    "total_rows": 0
                }

            # Step 3: Extract downloaded trading dates.
            trade_dates = [
                pd.Timestamp(index).date()
                for index in df.index
            ]

            # Step 4: Retrieve existing records in one query.
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

            # Step 5: Insert or update NIFTY 50 records.
            for index, row in df.iterrows():

                trade_date = pd.Timestamp(index).date()

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

            # Step 6: Commit all NIFTY 50 changes.
            db.commit()

            result = {
                "symbol": symbol,
                "inserted": inserted,
                "updated": updated,
                "total_rows": len(df)
            }

            logger.info(
                "NIFTY 50 index history loaded successfully.",
                extra={
                    "event": "nifty_index_history_completed",
                    "symbol": symbol,
                    "records_inserted": inserted,
                    "records_updated": updated,
                    "records_count": len(df)
                }
            )

            return result

        except Exception as exc:

            # Step 7: Roll back failed database operations.
            db.rollback()

            logger.exception(
                "Failed to load NIFTY 50 index history.",
                extra={
                    "event": "nifty_index_history_failed",
                    "symbol": symbol
                }
            )

            raise RuntimeError(
                "Failed to load NIFTY 50 index history."
            ) from exc
    
    
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
        """
        Load or update historical data for a sector index.

        Execution Steps:
            1. Validate the historical period.
            2. Retrieve the Yahoo Finance ticker from the sector mapping.
            3. Download sector index historical data.
            4. Normalize the downloaded data.
            5. Retrieve existing sector records for downloaded dates.
            6. Update existing records.
            7. Insert missing records.
            8. Commit the database transaction.
            9. Log the loading statistics.
            10. Return the loading summary.

        Args:
            db: Active SQLAlchemy database session.
            sector: Sector enum identifying the sector index.
            years: Number of historical years to download.

        Returns:
            Dictionary containing symbol, inserted, updated and total_rows.

        Raises:
            ValueError: If the historical period or sector mapping is invalid.
            RuntimeError: If downloading or database operations fail.
        """

        if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
            raise ValueError("Years must be a positive integer.")

        try:
            # Step 1: Resolve the Yahoo Finance ticker and database symbol.
            yahoo_symbol = SECTOR_INDEX_SYMBOLS[sector]
            symbol = sector.value

        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"Invalid or unsupported sector: {sector}"
            ) from exc

        logger.info(
            "Starting sector historical data loading.",
            extra={
                "event": "load_sector_history_started",
                "symbol": symbol,
                "period": f"{years}y"
            }
        )

        try:
            # Step 2: Download historical sector data.
            history = self.download_history(
                symbol=yahoo_symbol,
                period=f"{years}y"
            )

            # Step 3: Normalize downloaded data.
            df = self._prepare_history_dataframe(history)

            if df.empty:
                logger.warning(
                    "No historical data received for sector.",
                    extra={
                        "event": "load_sector_history_empty",
                        "symbol": symbol
                    }
                )

                return {
                    "symbol": symbol,
                    "inserted": 0,
                    "updated": 0,
                    "total_rows": 0
                }

            # Step 4: Retrieve existing sector records in one query.
            trade_dates = [
                pd.Timestamp(index).date()
                for index in df.index
            ]

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

            # Step 5: Insert missing records or update existing records.
            for index, row in df.iterrows():

                trade_date = pd.Timestamp(index).date()
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

            # Step 6: Commit all sector changes.
            db.commit()

            result = {
                "symbol": symbol,
                "inserted": inserted,
                "updated": updated,
                "total_rows": len(df)
            }

            logger.info(
                "Sector historical data loaded successfully.",
                extra={
                    "event": "load_sector_history_completed",
                    "symbol": symbol,
                    "records_inserted": inserted,
                    "records_updated": updated,
                    "records_count": len(df)
                }
            )

            return result

        except Exception as exc:

            db.rollback()

            logger.exception(
                "Failed to load sector historical data.",
                extra={
                    "event": "load_sector_history_failed",
                    "symbol": symbol,
                    "yahoo_symbol": yahoo_symbol
                }
            )

            raise RuntimeError(
                f"Failed to load historical data for sector {symbol}."
            ) from exc

    
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