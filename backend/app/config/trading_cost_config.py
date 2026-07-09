from dataclasses import dataclass


@dataclass
class TradingCostConfig:

    #
    # Master Switch
    #

    enabled: bool = True

    #
    # Broker
    #

    broker: str = "dhan"

    #
    # Trading Type
    #

    trading_type: str = "delivery"
    # delivery
    # intraday
    # mtf

    #
    # Brokerage
    #

    brokerage_per_order: float = 0.0

    #
    # Taxes (%)
    #

    stt_percent: float = 0.10

    exchange_percent: float = 0.003069

    sebi_percent: float = 0.0001

    stamp_percent: float = 0.015

    gst_percent: float = 18

    #
    # DP Charges
    #

    dp_charge: float = 12.5

    #
    # Slippage
    #

    slippage_percent: float = 0.00