import pandas as pd

from sqlalchemy.orm import Session

from app.database.models import MarketData


class MovingAverageStrategy:

    def load_market_data(
        self,
        db: Session,
        symbol: str
    ):

        data = (

            db.query(MarketData)

            .filter(
                MarketData.symbol == symbol
            )

            .order_by(
                MarketData.date
            )

            .all()

        )

        return data

    def calculate_moving_averages(
        self,
        db: Session,
        symbol: str
    ):

        records = self.load_market_data(
            db,
            symbol
        )

        df = pd.DataFrame([

            {
                "date": x.date,
                "close": x.close
            }

            for x in records

        ])

        df["MA15"] = (

            df["close"]

            .rolling(15)

            .mean()

        )

        df["MA30"] = (

            df["close"]

            .rolling(30)

            .mean()

        )

        df["MA150"] = (

            df["close"]

            .rolling(150)

            .mean()

        )

        return df
    
    def generate_signals(
        self,
        db: Session,
        symbol: str
    ):

        df = self.calculate_moving_averages(
            db,
            symbol
        )

        signals = []

        for _, row in df.iterrows():

            signal = "HOLD"

            # Not enough data for all 3 moving averages
            if (
                pd.isna(row["MA15"])
                or pd.isna(row["MA30"])
                or pd.isna(row["MA150"])
            ):
                signal = "HOLD"

            # Bullish trend
            elif (
                row["MA15"] > row["MA30"] > row["MA150"]
            ):

                if row["close"] > row["MA15"]:
                    signal = "BUY"

                elif row["close"] < row["MA15"]:
                    signal = "SELL"

                else:
                    signal = "HOLD"

            # Not in a bullish trend
            else:
                signal = "HOLD"

            signals.append(
                {
                    "date": row["date"],
                    "close": float(row["close"]),
                    "MA15": None if pd.isna(row["MA15"]) else float(row["MA15"]),
                    "MA30": None if pd.isna(row["MA30"]) else float(row["MA30"]),
                    "MA150": None if pd.isna(row["MA150"]) else float(row["MA150"]),
                    "signal": signal
                }
            )

        return signals