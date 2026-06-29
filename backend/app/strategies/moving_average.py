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

                "open": x.open,

                "high": x.high,

                "low": x.low,

                "close": x.close,

                "volume": x.volume

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

        in_position = False

        waiting_breakout = False

        support_high = None
        support_low = None

        breakout_candle_count = 0

        max_breakout_wait = 5

        # Maximum distance allowed from MA15
        pullback_percent = 1.5

        for _, row in df.iterrows():

            signal = "HOLD"
            entry_price = None

            ma15 = row["MA15"]
            ma30 = row["MA30"]
            ma150 = row["MA150"]

            distance_from_ma = None
            near_ma15 = False

            bullish_candle = False
            touches_ma15 = False
            support_candle = False

            # Not enough data
            if (
                pd.isna(ma15)
                or pd.isna(ma30)
                or pd.isna(ma150)
            ):

                signal = "HOLD"

            else:

                bullish_trend = (

                    ma15 > ma30 > ma150

                )

                distance_from_ma = (

                    abs(

                        row["close"] - ma15

                    )

                    / ma15

                ) * 100

                near_ma15 = (

                    distance_from_ma <= pullback_percent

                )

                bullish_candle = (

                    row["close"] > row["open"]

                )

                touches_ma15 = (

                    row["low"] <= ma15

                )

                support_candle = (

                    bullish_trend

                    and

                    near_ma15

                    and

                    bullish_candle

                    and

                    touches_ma15

                )

                buy_condition = False

                sell_condition = (

                    row["close"] < ma15

                )

                if not in_position:

                    if support_candle:

                        waiting_breakout = True

                        support_high = row["high"]

                        support_low = row["low"]

                        breakout_candle_count = 0

                    elif waiting_breakout:

                        breakout_candle_count += 1

                        if row["high"] > support_high:

                            buy_condition = True

                            entry_price = support_high

                            waiting_breakout = False

                        elif breakout_candle_count >= max_breakout_wait:

                            waiting_breakout = False

                            support_high = None

                            support_low = None

                            breakout_candle_count = 0

                    if buy_condition:

                        signal = "BUY"

                        in_position = True

                    else:

                        signal = "HOLD"

                else:

                    if sell_condition:

                        signal = "SELL"

                        in_position = False

                        waiting_breakout = False

                        support_high = None

                        support_low = None

                        breakout_candle_count = 0

                    else:

                        signal = "HOLD"
            signals.append(
                {
                    "date": row["date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                    "MA15": None if pd.isna(ma15) else float(ma15),
                    "MA30": None if pd.isna(ma30) else float(ma30),
                    "MA150": None if pd.isna(ma150) else float(ma150),
                    "distance_from_ma": (
                        None if distance_from_ma is None
                        else round(distance_from_ma, 2)
                    ),
                    "near_ma15": near_ma15,
                    "bullish_candle": bullish_candle,
                    "touches_ma15": touches_ma15,
                    "support_candle": support_candle,
                    "waiting_breakout": waiting_breakout,
                    "breakout_candle_count": breakout_candle_count,
                    "support_high": (
                        None if support_high is None
                        else float(support_high)
                    ),
                    "support_low": (
                        None if support_low is None
                        else float(support_low)
                    ),
                    "entry_price": (
                        None if entry_price is None
                        else float(entry_price)
                    ),
                    "signal": signal
                }
            )

        return signals
