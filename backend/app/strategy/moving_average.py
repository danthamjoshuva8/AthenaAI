
import pandas as pd
from sqlalchemy.orm import Session

from app.config.backtest_config import BacktestConfig
from app.config.strategy_config import StrategyConfig
from app.database.models import MarketData
from app.utils.price_buffer import apply_entry_stop_buffer


# Load strategy-level parameters.
config = StrategyConfig()

# Percentage used to identify pullback conditions.
pullback_percent = config.pullback_percent

# Required volume multiplier for volume confirmation.
volume_multiplier = config.volume_multiplier

# Maximum allowed candle body percentage.
max_body_percent = config.max_body_percent

# Maximum allowed upper wick ratio.
max_upper_wick_ratio = config.max_upper_wick_ratio

# Minimum required lower wick ratio.
min_lower_wick_ratio = config.min_lower_wick_ratio

# Maximum number of candles to wait for a breakout.
max_breakout_wait = config.breakout_wait


class MovingAverageStrategy:
    """
    Implements a moving average-based trading strategy.

    Loads historical market data, calculates moving averages
    and volume averages, and maintains trade execution state.
    """

    def __init__(
        self,
        config: BacktestConfig
    ):
        """
        Initialize the strategy with backtesting configuration.

        Args:
            config: Configuration containing strategy parameters.
        """
        self.config = config

    def load_market_data(
        self,
        db: Session,
        symbol: str,
        start_date=None,
        end_date=None
    ):
        """
        Load historical market data for a symbol.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to retrieve.
            start_date: Optional starting date for the data.
            end_date: Optional ending date for the data.

        Returns:
            Market data records ordered by date.
        """
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
        """
        Calculate configured moving averages and volume average.

        Loads historical OHLCV data and calculates short, medium,
        and long moving averages along with the 20-period average
        volume.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to process.
            start_date: Optional starting date for the data.
            end_date: Optional ending date for the data.

        Returns:
            DataFrame containing market data and calculated indicators.
            Returns an empty DataFrame when insufficient data is available.
        """
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

        # Retrieve moving average periods from strategy configuration.
        short_ma = self.config.strategy.short_ma
        medium_ma = self.config.strategy.medium_ma
        long_ma = self.config.strategy.long_ma

        if len(df) < long_ma:
            return pd.DataFrame()

        # Calculate short, medium, and long moving averages.
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

        # Calculate the 20-period average trading volume.
        df["VOLUME20"] = (
            df["volume"]
            .rolling(20)
            .mean()
        )

        # True Range calculation (currently disabled).
        # df["TR"] = pd.concat([
        #     df["high"] - df["low"],
        #     (df["high"] - df["close"].shift()).abs(),
        #     (df["low"] - df["close"].shift()).abs()
        # ], axis=1).max(axis=1)

        # 14-period Average True Range (currently disabled).
        # df["ATR"] = df["TR"].rolling(14).mean()

        # ATR expressed as a percentage of closing price (currently disabled).
        # df["ATR_PERCENT"] = (
        #     (df["ATR"] / df["close"]) * 100
        # )

        return df

    def reset_trade_state(self):
        """
        Initialize or reset the state of the current trade.

        Returns:
            Dictionary containing the default trade execution state.
        """
        return {
            "in_position": False,             # Whether a trade is currently active.
            "current_entry_price": None,      # Entry price of the active trade.
            "current_stop_loss": None,        # Current stop-loss price.
            "target_2r": None,                # Price target at 2R.
            "target_3r": None,                # Price target at 3R.
            "partial_exit_2r": False,         # Whether the 2R partial exit is completed.
            "partial_exit_3r": False,         # Whether the 3R partial exit is completed.
            "waiting_breakout": False,        # Whether a breakout confirmation is pending.
            "support_high": None,             # High of the identified support candle.
            "support_low": None,              # Low of the identified support candle.
            "breakout_candle_count": 0        # Number of candles elapsed while waiting for breakout.
        }
 
    
    def generate_signals(
        self,
        db,
        symbol,
        start_date=None,
        end_date=None
    ):
        """
        Generate daily BUY, SELL, and HOLD signals for a stock.

        Uses moving average alignment, pullback conditions, candle
        quality, and volume confirmation to identify support candles
        and subsequent breakout entries.

        A BUY signal is generated when price breaks above the identified
        support candle high. A SELL signal is generated when the closing
        price falls below the short moving average.

        Target-based and trailing exit execution is handled separately
        by the BacktestEngine.

        Args:
            db: SQLAlchemy database session.
            symbol: Stock symbol to generate signals for.
            start_date: Optional starting date for historical data.
            end_date: Optional ending date for historical data.

        Returns:
            List of dictionaries containing daily market data, indicators,
            trading conditions, trade state, and generated signals.
        """

        # Calculate moving averages and load historical market data.
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

        # Initialize trade execution state.
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

        # Entry and stop-loss buffers are disabled by default.
        entry_buffer_enabled = False
        stoploss_buffer_enabled = False

        # Process historical candles in chronological order.
        for index, row in df.iterrows():

            # Default signal and trade execution values for each candle.
            signal = "HOLD"
            entry_price = None
            stop_loss = None
            exit_price = None
            exit_reason = None

            buy_condition = False
            sell_condition = False

            # Retrieve moving average values for the current candle.
            short_ma = row["MA_SHORT"]
            medium_ma = row["MA_MEDIUM"]
            long_ma = row["MA_LONG"]

            # Initialize candle and pullback evaluation metrics.
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

            # Not enough moving average data to evaluate the strategy.
            if (
                pd.isna(short_ma)
                or pd.isna(medium_ma)
                or pd.isna(long_ma)
            ):
                signal = "HOLD"

            else:

                # Confirm bullish moving average alignment.
                bullish_trend = (
                    short_ma > medium_ma > long_ma
                )

                # Calculate closing price distance from the short moving average.
                distance_from_ma = (
                    abs(
                        row["close"] - short_ma
                    )
                    / short_ma
                ) * 100

                # Check whether price is sufficiently close to the short MA.
                near_short_ma = (
                    distance_from_ma <= pullback_percent
                )

                # Identify bullish candles.
                bullish_candle = (
                    row["close"] > row["open"]
                )

                # Calculate candle body size and percentage.
                body_size = abs(
                    row["close"] - row["open"]
                )

                body_percent = (
                    body_size
                    / row["open"]
                ) * 100

                # Calculate upper and lower candle wick sizes.
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

                # Calculate wick-to-body ratios.
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

                # Evaluate candle body and wick quality.
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

                # Candle must satisfy all configured quality conditions.
                quality_pass = (
                    good_body
                    and
                    good_upper_wick
                    and
                    good_lower_wick
                )

                # Check whether the candle touches the short MA
                # and closes above it.
                touches_short_ma = (
                    row["low"] <= short_ma
                    and
                    row["close"] > short_ma
                )

                # Confirm volume is above its 20-period average threshold.
                if not pd.isna(row["VOLUME20"]):
                    volume_confirmation = (
                        row["volume"] >= row["VOLUME20"] * volume_multiplier
                        and row["volume"] > 0
                    )

                # Identify a valid support candle.
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

                # Evaluate entry conditions only when no trade is active.
                if not in_position:

                    # Store the support candle and wait for a breakout.
                    if support_candle:

                        waiting_breakout = True
                        support_high = row["high"]
                        support_low = row["low"]

                        current_index = index

                        # Include the previous bearish candle's low
                        # when identifying the support range.
                        if current_index > 0:

                            previous = df.iloc[current_index - 1]

                            if previous["close"] < previous["open"]:

                                support_low = min(
                                    previous["low"],
                                    row["low"]
                                )

                        # Start counting candles after support identification.
                        breakout_candle_count = 0

                    elif waiting_breakout:

                        # Count candles while waiting for breakout confirmation.
                        breakout_candle_count += 1

                        # Confirm breakout when price closes above support high.
                        if (
                            row["close"] > support_high
                        ):

                            buy_condition = True

                            # Determine entry price using support high
                            # and the current candle's opening price.
                            entry_price = max(
                                support_high,
                                row["open"]
                            )

                            stop_loss = support_low

                            # Apply optional entry and stop-loss buffers.
                            entry_price, stop_loss = apply_entry_stop_buffer(
                                entry_price,
                                stop_loss,
                                entry_enabled=entry_buffer_enabled,
                                stop_enabled=stoploss_buffer_enabled
                            )

                            # Calculate the additional entry price caused by buffering.
                            buffer_used = entry_price - max(
                                support_high,
                                row["open"]
                            )

                            current_stop_loss = stop_loss
                            waiting_breakout = False

                        # Cancel the breakout setup if the waiting period expires.
                        elif breakout_candle_count >= max_breakout_wait:

                            waiting_breakout = False
                            support_high = None
                            support_low = None
                            current_stop_loss = None
                            breakout_candle_count = 0

                # Execute BUY signal and initialize trade targets.
                if buy_condition:

                    signal = "BUY"
                    in_position = True

                    # Clear the completed support and breakout setup.
                    waiting_breakout = False
                    support_high = None
                    support_low = None

                    current_stop_loss = stop_loss
                    current_entry_price = entry_price

                    # Calculate per-share risk and 2R/3R price targets.
                    risk_per_share = current_entry_price - current_stop_loss

                    target_2r = current_entry_price + (2 * risk_per_share)
                    target_3r = current_entry_price + (3 * risk_per_share)

                    # Reset partial exit tracking for the new trade.
                    partial_exit_2r = False
                    partial_exit_3r = False

                    breakout_candle_count = 0

                # Evaluate exit conditions when a position is active.
                elif in_position:

                    # Only generate MA SELL.
                    # All target/trailing logic is handled by BacktestEngine.
                    if row["close"] < short_ma:

                        signal = "SELL"
                        exit_price = row["close"]
                        exit_reason = "SHORT_MA_BREAK"

                        # Close the active trade and reset its state.
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

            # Store the current candle's market data, indicators,
            # trading conditions, and execution state.
            signals.append(
                {
                    "date": row["date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),

                    # 20-period average volume.
                    "volume20": (
                        None
                        if pd.isna(row["VOLUME20"])
                        else round(float(row["VOLUME20"]), 2)
                    ),

                    # Volume confirmation result.
                    "volume_confirmation": volume_confirmation,

                    # Moving average periods and their current values.
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

                    # Pullback and support candle evaluation.
                    "distance_from_ma": (
                        None if distance_from_ma is None
                        else round(distance_from_ma, 2)
                    ),
                    "near_short_ma": near_short_ma,
                    "bullish_candle": bullish_candle,
                    "touches_short_ma": touches_short_ma,
                    "support_candle": support_candle,

                    # Breakout waiting state and support price levels.
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

                    # Trade entry and exit prices.
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

                    # Current trade status.
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

                    # Candle quality metrics.
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

                    # Calculated risk-reward targets.
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

                    # Partial exit execution status.
                    "partial_exit_2r": partial_exit_2r,
                    "partial_exit_3r": partial_exit_3r,

                    # Difference between buffered and original entry price.
                    "buffer": (
                        None
                        if entry_price is None
                        else round(buffer_used, 2)
                    )
                }
            )

        return signals

    
