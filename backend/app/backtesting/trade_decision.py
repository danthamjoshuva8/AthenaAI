from dataclasses import dataclass


@dataclass
class TradeDecision:

    symbol: str

    date: str

    decision: str

    reason: str

    score: float = 0

    capital_required: float = 0

    available_capital: float = 0