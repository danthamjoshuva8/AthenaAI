from app.config.trading_cost_config import TradingCostConfig


class TradingCostEngine:

    def __init__(self):

        self.config = TradingCostConfig()

    def calculate_trade_cost(
        self,
        buy_value: float,
        sell_value: float
    ):

        if not self.config.enabled:

            return {

                "brokerage": 0,

                "stt": 0,

                "exchange": 0,

                "sebi": 0,

                "stamp": 0,

                "gst": 0,

                "dp_charge": 0,

                "slippage": 0,

                "total": 0

            }

        #
        # Brokerage
        #

        if self.config.trading_type == "delivery":

            brokerage = 0

        else:

            brokerage = min(
                buy_value * 0.0003,
                20
            )

            brokerage += min(
                sell_value * 0.0003,
                20
            )

        #
        # Taxes
        #

        turnover = buy_value + sell_value

        stt = turnover * self.config.stt_percent / 100

        exchange = turnover * self.config.exchange_percent / 100

        sebi = turnover * self.config.sebi_percent / 100

        stamp = buy_value * self.config.stamp_percent / 100

        gst = (

            brokerage + exchange

        ) * self.config.gst_percent / 100

        dp = 0

        if self.config.trading_type == "delivery":

            dp = self.config.dp_charge

        slippage = (

            turnover

            * self.config.slippage_percent

            / 100

        )

        total = (

            brokerage

            + stt

            + exchange

            + sebi

            + stamp

            + gst

            + dp

            + slippage

        )

        return {

            "brokerage": round(
                brokerage,
                2
            ),

            "stt": round(
                stt,
                2
            ),

            "exchange": round(
                exchange,
                2
            ),

            "sebi": round(
                sebi,
                2
            ),

            "stamp": round(
                stamp,
                2
            ),

            "gst": round(
                gst,
                2
            ),

            "dp_charge": round(
                dp,
                2
            ),

            "slippage": round(
                slippage,
                2
            ),

            "total": round(
                total,
                2
            )

        }