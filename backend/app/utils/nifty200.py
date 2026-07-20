# import pandas as pd


# def get_nifty200_symbols():

#     url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"

#     df = pd.read_csv(url)

#     symbols = []

#     for symbol in df["Symbol"]:

#         symbols.append(f"{symbol}.NS")

#     return symbols

from pathlib import Path

import pandas as pd


def get_nifty200_symbols():

    csv_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "MW-NIFTY-200-17-Jul-2026.csv"
    )

    df = pd.read_csv(csv_path)

    symbols = []

    for symbol in df["SYMBOL"]:

        # Skip the index row
        if symbol == "NIFTY 200":
            continue

        symbols.append(f"{symbol}.NS")

    return symbols