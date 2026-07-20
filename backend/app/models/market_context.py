from dataclasses import dataclass


@dataclass
class MarketContext:

    trend: str

    close: float

    ma150: float

    ma150_slope: float

    score: float