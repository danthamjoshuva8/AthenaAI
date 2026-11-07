# import pandas as pd


# def load_nifty200_symbols():

#     url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"

#     df = pd.read_csv(url)

#     symbols = []

#     for symbol in df["Symbol"]:

#         symbols.append(f"{symbol}.NS")

#     return symbols


import logging
import time
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


def load_nifty200_symbols() -> list[str]:
    """
    Load and normalize NIFTY 200 stock symbols.

    Reads the SYMBOL column from the configured CSV file,
    skips the index row, removes invalid entries and duplicates,
    and appends the Yahoo Finance .NS suffix.

    Returns:
        list[str]: Unique Yahoo Finance stock symbols.

    Raises:
        FileNotFoundError: If the CSV file is missing.
        ValueError: If the CSV is empty or invalid.
        RuntimeError: If an unexpected processing error occurs.
    """

    start_time = time.perf_counter()

    # --------------------------------------------------
    # Step 1: Resolve CSV file path
    # --------------------------------------------------

    csv_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "MW-NIFTY-200-17-Jul-2026.csv"
    )

    logger.info(
        "NIFTY 200 symbol loading started",
        extra={
            "event": "nifty200_loading_started",
            "file_path": str(csv_path)
        }
    )

    try:
        # --------------------------------------------------
        # Step 2: Validate CSV file availability
        # --------------------------------------------------

        if not csv_path.is_file():
            raise FileNotFoundError(
                f"NIFTY 200 CSV file not found: {csv_path}"
            )

        # --------------------------------------------------
        # Step 3: Read CSV file
        # --------------------------------------------------

        df = pd.read_csv(csv_path)

        if df.empty:
            raise ValueError(
                "NIFTY 200 CSV file is empty."
            )

        # --------------------------------------------------
        # Step 4: Validate required column
        # --------------------------------------------------

        if "SYMBOL" not in df.columns:
            raise ValueError(
                "NIFTY 200 CSV is missing the SYMBOL column."
            )

        # --------------------------------------------------
        # Step 5: Extract and normalize symbols
        # --------------------------------------------------

        symbols = []

        invalid_count = 0

        for raw_symbol in df["SYMBOL"]:

            if pd.isna(raw_symbol):
                invalid_count += 1
                continue

            symbol = str(raw_symbol).strip().upper()

            # Skip empty values and index rows.
            if not symbol or symbol == "NIFTY 200":
                invalid_count += 1
                continue

            # Avoid adding the suffix twice.
            if symbol.endswith(".NS"):
                symbol = symbol[:-3]

            # Reject unexpected symbol formatting.
            if (
                not symbol
                or any(character.isspace() for character in symbol)
            ):
                invalid_count += 1
                continue

            symbols.append(f"{symbol}.NS")

        # --------------------------------------------------
        # Step 6: Remove duplicates while preserving order
        # --------------------------------------------------

        original_count = len(symbols)

        symbols = list(dict.fromkeys(symbols))

        duplicate_count = original_count - len(symbols)

        # --------------------------------------------------
        # Step 7: Validate final symbol collection
        # --------------------------------------------------

        if not symbols:
            raise ValueError(
                "No valid stock symbols found in the NIFTY 200 CSV."
            )

        # --------------------------------------------------
        # Step 8: Log successful completion
        # --------------------------------------------------

        duration = time.perf_counter() - start_time

        logger.info(
            "NIFTY 200 symbols loaded successfully",
            extra={
                "event": "nifty200_loading_completed",
                "symbols_count": len(symbols),
                "invalid_count": invalid_count,
                "duplicate_count": duplicate_count,
                "duration_seconds": round(duration, 4),
                "file_path": str(csv_path)
            }
        )

        return symbols

    except FileNotFoundError:
        duration = time.perf_counter() - start_time

        logger.exception(
            "NIFTY 200 CSV file not found",
            extra={
                "event": "nifty200_file_not_found",
                "file_path": str(csv_path),
                "duration_seconds": round(duration, 4)
            }
        )

        raise

    except ValueError:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Invalid NIFTY 200 CSV data",
            extra={
                "event": "nifty200_invalid_data",
                "file_path": str(csv_path),
                "duration_seconds": round(duration, 4)
            }
        )

        raise

    except Exception as ex:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Failed to load NIFTY 200 stock symbols",
            extra={
                "event": "nifty200_loading_failed",
                "file_path": str(csv_path),
                "duration_seconds": round(duration, 4)
            }
        )

        raise RuntimeError(
            "Unable to load NIFTY 200 stock symbols."
        ) from ex
