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

        df["VOLUME20"] = (
            df["volume"]
            .rolling(20)
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

        # Position status
        in_position = False

        # Breakout waiting variables
        waiting_breakout = False

        support_high = None

        support_low = None

        current_stop_loss = None

        current_entry_price = None

        target_2r = None

        target_3r = None

        partial_exit_done = False

        breakout_candle_count = 0

        max_breakout_wait = 5

        # Maximum distance allowed from MA15
        pullback_percent = 1.5
        volume_multiplier = 0.5
        max_body_percent = 3.0

        max_upper_wick_ratio = 1.0

        min_lower_wick_ratio = 0.20

        for index,row in df.iterrows():

            signal = "HOLD"

            entry_price = None

            stop_loss = None

            exit_price = None

            exit_reason = None

            buy_condition = False

            sell_condition = False

            ma15 = row["MA15"]
            ma30 = row["MA30"]
            ma150 = row["MA150"]

            distance_from_ma = None
            near_ma15 = False

            bullish_candle = False
            touches_ma15 = False
            support_candle = False
            volume_confirmation = False
            body_percent = None

            upper_wick_ratio = None

            lower_wick_ratio = None

            quality_pass = False

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

                body_size = abs(

                    row["close"] - row["open"]

                )

                body_percent = (

                    body_size

                    / row["open"]

                ) * 100

                upper_wick = (

                    row["high"]

                    - max(

                        row["open"],

                        row["close"]

                    )

                )

                lower_wick = (

                    min(

                        row["open"],

                        row["close"]

                    )

                    - row["low"]

                )

                if body_size > 0:

                    upper_wick_ratio = (

                        upper_wick

                        / body_size

                    )

                    lower_wick_ratio = (

                        lower_wick

                        / body_size

                    )

                else:

                    upper_wick_ratio = 0

                    lower_wick_ratio = 0

                good_body = (

                    body_percent

                    <=

                    max_body_percent

                )

                good_upper_wick = (

                    upper_wick_ratio

                    <=

                    max_upper_wick_ratio

                )

                good_lower_wick = (

                    lower_wick_ratio

                    >=

                    min_lower_wick_ratio

                )

                quality_pass = (

                    good_body

                    and

                    good_upper_wick

                    and

                    good_lower_wick

                )

                touches_ma15 = (

                    row["low"] <= ma15

                    and

                    row["close"] > ma15

                )

                if not pd.isna(row["VOLUME20"]):

                    volume_confirmation = (
                        row["volume"] >= row["VOLUME20"] * volume_multiplier
                        and row["volume"] > 0
                    )

                support_candle = (

                    bullish_trend

                    and

                    near_ma15

                    and

                    bullish_candle

                    and

                    touches_ma15

                    and

                    volume_confirmation

                    and

                    quality_pass

                )

                buy_condition = False

                if not in_position:

                    if support_candle:

                        waiting_breakout = True

                        support_high = row["high"]

                        support_low = row["low"]

                        current_index = index

                        if current_index > 0:

                            previous = df.iloc[current_index - 1]

                            if previous["close"] < previous["open"]:

                                support_low = min(

                                    previous["low"],

                                    row["low"]

                                )

                        breakout_candle_count = 0

                    elif waiting_breakout:

                        breakout_candle_count += 1

                        if (

                            row["close"] > support_high

                        ):

                            buy_condition = True

                            entry_price = max(

                                support_high,

                                row["open"]

                            )

                            stop_loss = support_low

                            current_stop_loss = stop_loss

                            waiting_breakout = False

                        elif breakout_candle_count >= max_breakout_wait:

                            waiting_breakout = False

                            support_high = None

                            support_low = None
                            current_stop_loss=None

                            breakout_candle_count = 0

                if buy_condition:

                    signal = "BUY"

                    in_position = True

                    waiting_breakout = False

                    support_high = None

                    support_low = None

                    current_stop_loss = stop_loss

                    current_entry_price = entry_price

                    risk_per_share = current_entry_price - current_stop_loss

                    target_2r = current_entry_price + (2 * risk_per_share)

                    target_3r = current_entry_price + (3 * risk_per_share)

                    partial_exit_done = False

                    breakout_candle_count = 0

                elif in_position:

                    #
                    # PARTIAL EXIT
                    #

                    if (

                        not partial_exit_done

                        and

                        row["high"] >= target_2r

                    ):

                        signal = "PARTIAL_EXIT"

                        exit_price = target_2r

                        exit_reason = "TARGET_2R"

                        partial_exit_done = True

                    #
                    # FINAL TARGET
                    #

                    elif (
                        partial_exit_done
                        and
                        row["high"] >= target_3r
                    ):

                        signal = "SELL"

                        exit_price = target_3r

                        exit_reason = "TARGET_3R"

                        in_position = False

                        current_stop_loss = None

                        current_entry_price = None

                        target_2r = None

                        target_3r = None

                        partial_exit_done = False

                    #
                    # MA15 EXIT
                    #

                    elif row["close"] < ma15:

                        signal = "SELL"

                        exit_price = row["close"]

                        exit_reason = "MA15_BREAK"

                        in_position = False

                        current_stop_loss = None

                        current_entry_price = None

                        target_2r = None

                        target_3r = None

                        partial_exit_done = False

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
                    "volume20": (

                        None

                        if pd.isna(row["VOLUME20"])

                        else round(float(row["VOLUME20"]), 2)

                    ),

                    "volume_confirmation": volume_confirmation,
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
                        None
                        if entry_price is None
                        else float(entry_price)
                    ),
                    "exit_price": (

                        None

                        if exit_price is None

                        else float(exit_price)

                    ),

                    "exit_reason": exit_reason,
                    "trade_status": (

                        "OPEN"

                        if in_position

                        else "CLOSED"

                    ),
                    "stop_loss": (
                        None
                        if current_stop_loss is None
                        else float(current_stop_loss)
                    ),

                    "in_position": in_position,
                    "signal": signal,
                    "body_percent": (
                        None
                        if body_percent is None
                        else round(body_percent, 2)
                    ),

                    "upper_wick_ratio": (
                        None
                        if upper_wick_ratio is None
                        else round(upper_wick_ratio, 2)
                    ),

                    "lower_wick_ratio": (
                        None
                        if lower_wick_ratio is None
                        else round(lower_wick_ratio, 2)
                    ),

                    "quality_pass": quality_pass,
                    "target_2r": (
                        None
                        if target_2r is None
                        else round(target_2r, 2)
                    ),

                    "target_3r": (
                        None
                        if target_3r is None
                        else round(target_3r, 2)
                    ),

                    "partial_exit_done": partial_exit_done
                }
            )

        return signals
