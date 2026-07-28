import pandas as pd

from sqlalchemy.orm import Session

from app.database.models import MarketData
from app.utils.price_buffer import apply_entry_stop_buffer
from app.config.strategy_config import StrategyConfig
from app.config.backtest_config import BacktestConfig
from app.config.backtest_config import ExitStrategyType

config = StrategyConfig()

pullback_percent = config.pullback_percent

volume_multiplier = config.volume_multiplier

max_body_percent = config.max_body_percent

max_upper_wick_ratio = config.max_upper_wick_ratio

min_lower_wick_ratio = config.min_lower_wick_ratio

max_breakout_wait = config.breakout_wait


class MovingAverageStrategy:

    def __init__(
        self,
        config: BacktestConfig
    ):

        self.config = config

    def load_market_data(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):

        query = (

            db.query(MarketData)

            .filter(

                MarketData.symbol == symbol

            )

        )

        if start_date:

            query = query.filter(

                MarketData.date >= start_date

            )

        if end_date:

            query = query.filter(

                MarketData.date <= end_date

            )

        data = (

            query

            .order_by(

                MarketData.date

            )

            .all()

        )

        return data

    def calculate_moving_averages(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):

        records = self.load_market_data(
            db,
            symbol,
            start_date,
            end_date
        )

        print(symbol)
        print("Records:", len(records))

        if len(records) == 0:
            return pd.DataFrame()

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

        print(df.columns.tolist())
        print(df.head())

        print(symbol)
        print("Rows:", len(df))

        if df.empty:
            return df

        short_ma = self.config.strategy.short_ma

        medium_ma = self.config.strategy.medium_ma

        long_ma = self.config.strategy.long_ma

        if len(df) < long_ma:
            return pd.DataFrame()

        df["MA_SHORT"] = (
            df["close"]
            .rolling(short_ma)
            .mean()
        )

        df["MA_MEDIUM"] = (
            df["close"]
            .rolling(medium_ma)
            .mean()
        )

        df["MA_LONG"] = (
            df["close"]
            .rolling(long_ma)
            .mean()
        )

        df["VOLUME20"] = (
            df["volume"]
            .rolling(20)
            .mean()
        )

        # # True Range
        # df["TR"] = pd.concat([
        #     df["high"] - df["low"],
        #     (df["high"] - df["close"].shift()).abs(),
        #     (df["low"] - df["close"].shift()).abs()
        # ], axis=1).max(axis=1)

        # # 14-day ATR
        # df["ATR"] = df["TR"].rolling(14).mean()

        # # ATR as % of Close
        # df["ATR_PERCENT"] = (
        #     (df["ATR"] / df["close"]) * 100
        # )

        return df

    def reset_trade_state(self):

        return {

            "in_position": False,

            "current_entry_price": None,

            "current_stop_loss": None,

            "target_2r": None,

            "target_3r": None,

            "partial_exit_2r": False,

            "partial_exit_3r": False,

            "waiting_breakout": False,

            "support_high": None,

            "support_low": None,

            "breakout_candle_count": 0

        }
    
    def generate_signals(
        self,
        db,
        symbol,
        start_date=None,
        end_date=None
    ):

        df = self.calculate_moving_averages(
            db,
            symbol,
            start_date,
            end_date
        )

        if df.empty:
            return []

        signals = []

        strategy = self.config.exit_strategy

        # Position status
        in_position = False

        state = self.reset_trade_state()

        in_position = state["in_position"]

        current_entry_price = state["current_entry_price"]

        current_stop_loss = state["current_stop_loss"]

        target_2r = state["target_2r"]

        target_3r = state["target_3r"]

        partial_exit_2r = state["partial_exit_2r"]

        partial_exit_3r = state["partial_exit_3r"]

        waiting_breakout = state["waiting_breakout"]

        support_high = state["support_high"]

        support_low = state["support_low"]

        breakout_candle_count = state["breakout_candle_count"]
        
        entry_buffer_enabled = False
        stoploss_buffer_enabled = False

        for index,row in df.iterrows():

            signal = "HOLD"

            entry_price = None

            stop_loss = None

            exit_price = None

            exit_reason = None

            buy_condition = False

            sell_condition = False

            short_ma = row["MA_SHORT"]

            medium_ma = row["MA_MEDIUM"]

            long_ma = row["MA_LONG"]

            distance_from_ma = None
            near_short_ma = False

            bullish_candle = False
            touches_short_ma = False
            support_candle = False
            volume_confirmation = False
            body_percent = None

            upper_wick_ratio = None

            lower_wick_ratio = None

            quality_pass = False

            # ma15_slope = None
            # ma30_slope = None
            # ma150_slope = None

            # distance_from_15ma = None
            # distance_from_30ma = None
            # distance_from_150ma = None

            # trend_alignment = False

            # ma15_30_gap = None
            # ma30_150_gap = None

            # # NEW
            # atr = None
            # atr_percent = None

            # Not enough data
            if (
                pd.isna(short_ma)
                or pd.isna(medium_ma)
                or pd.isna(long_ma)
            ):

                signal = "HOLD"

            else:

                bullish_trend = (

                    short_ma > medium_ma > long_ma

                )

                # #
                # # Trend Metrics
                # #

                # trend_alignment = bullish_trend

                # distance_from_15ma = round(
                #     ((row["close"] - short_ma) / short_ma) * 100,
                #     2
                # )

                # distance_from_30ma = round(
                #     ((row["close"] - medium_ma) / medium_ma) * 100,
                #     2
                # )

                # distance_from_150ma = round(
                #     ((row["close"] - long_ma) / long_ma) * 100,
                #     2
                # )

                # ma15_30_gap = round(
                #     ((short_ma - medium_ma) / medium_ma) * 100,
                #     2
                # )

                # ma30_150_gap = round(
                #     ((medium_ma - long_ma) / long_ma) * 100,
                #     2
                # )

                # #
                # # MA Slopes
                # #

                # previous = df.iloc[max(0, index - 5)]

                # if index >= 5:

                #     ma15_slope = round(
                #         (short_ma - previous["MA_SHORT"]) / 5,
                #         4
                #     )

                #     ma30_slope = round(
                #         (medium_ma - previous["MA_MEDIUM"]) / 5,
                #         4
                #     )

                #     ma150_slope = round(
                #         (long_ma - previous["MA_LONG"]) / 5,
                #         4
                #     )

                # # ATR (14-day)

                # if index >= 14:

                #     tr_values = []

                #     for i in range(index - 13, index + 1):

                #         current = df.iloc[i]

                #         previous_close = (
                #             df.iloc[i - 1]["close"]
                #             if i > 0
                #             else current["close"]
                #         )

                #         tr = max(
                #             current["high"] - current["low"],
                #             abs(current["high"] - previous_close),
                #             abs(current["low"] - previous_close)
                #         )

                #         tr_values.append(tr)

                #     atr = round(sum(tr_values) / 14, 2)

                #     atr_percent = round(
                #         (atr / row["close"]) * 100,
                #         2
                #     )

                distance_from_ma = (

                    abs(

                        row["close"] - short_ma

                    )

                    / short_ma

                ) * 100

                near_short_ma = (

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

                # atr = None
                # atr_percent = None

                # if not pd.isna(row["ATR"]):
                #     atr = round(float(row["ATR"]), 2)

                # if not pd.isna(row["ATR_PERCENT"]):
                #     atr_percent = round(float(row["ATR_PERCENT"]), 2)

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

                touches_short_ma = (

                    row["low"] <= short_ma

                    and

                    row["close"] > short_ma

                )

                if not pd.isna(row["VOLUME20"]):

                    volume_confirmation = (
                        row["volume"] >= row["VOLUME20"] * volume_multiplier
                        and row["volume"] > 0
                    )

                support_candle = (

                    bullish_trend

                    and

                    near_short_ma

                    and

                    bullish_candle

                    and

                    touches_short_ma

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

                            #
                            # Apply Entry / Stop Buffer
                            #

                            entry_price, stop_loss = apply_entry_stop_buffer(

                                entry_price,

                                stop_loss,

                                entry_enabled=entry_buffer_enabled,
                                stop_enabled=stoploss_buffer_enabled

                            )

                            buffer_used = entry_price - max(

                                support_high,

                                row["open"]

                            )

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

                    partial_exit_2r = False

                    partial_exit_3r = False

                    breakout_candle_count = 0

                elif in_position:

                    #
                    # Only generate MA SELL.
                    # All target/trailing logic is handled by BacktestEngine.
                    #

                    if row["close"] < short_ma:

                        signal = "SELL"

                        exit_price = row["close"]

                        exit_reason = "SHORT_MA_BREAK"

                        in_position = False

                        state = self.reset_trade_state()

                        in_position = state["in_position"]
                        current_entry_price = state["current_entry_price"]
                        current_stop_loss = state["current_stop_loss"]
                        target_2r = state["target_2r"]
                        target_3r = state["target_3r"]
                        partial_exit_2r = state["partial_exit_2r"]
                        partial_exit_3r = state["partial_exit_3r"]
                        waiting_breakout = state["waiting_breakout"]
                        support_high = state["support_high"]
                        support_low = state["support_low"]
                        breakout_candle_count = state["breakout_candle_count"]

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
                    "moving_averages": {
                        "short": {
                            "period": self.config.strategy.short_ma,
                            "value": None if pd.isna(short_ma) else float(short_ma)
                        },
                        "medium": {
                            "period": self.config.strategy.medium_ma,
                            "value": None if pd.isna(medium_ma) else float(medium_ma)
                        },
                        "long": {
                            "period": self.config.strategy.long_ma,
                            "value": None if pd.isna(long_ma) else float(long_ma)
                        }
                    },
                    "distance_from_ma": (
                        None if distance_from_ma is None
                        else round(distance_from_ma, 2)
                    ),
                    "near_short_ma": near_short_ma,
                    "bullish_candle": bullish_candle,
                    "touches_short_ma": touches_short_ma,
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
                    # "trend_alignment": trend_alignment,

                    # "ma15_slope": ma15_slope,
                    # "ma30_slope": ma30_slope,
                    # "ma150_slope": ma150_slope,

                    # "distance_from_15ma": distance_from_15ma,
                    # "distance_from_30ma": distance_from_30ma,
                    # "distance_from_150ma": distance_from_150ma,

                    # "ma15_30_gap": ma15_30_gap,
                    # "ma30_150_gap": ma30_150_gap,
                    # "atr": atr,
                    # "atr_percent": atr_percent,
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

                    "partial_exit_2r": partial_exit_2r,

                    "partial_exit_3r": partial_exit_3r,
                    "buffer": (

                        None

                        if entry_price is None

                        else round(buffer_used, 2)

                    )
                }
            )

        return signals
