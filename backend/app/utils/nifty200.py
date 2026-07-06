import pandas as pd


def get_nifty200_symbols():

    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"

    df = pd.read_csv(url)

    symbols = []

    for symbol in df["Symbol"]:

        symbols.append(f"{symbol}.NS")

    return symbols