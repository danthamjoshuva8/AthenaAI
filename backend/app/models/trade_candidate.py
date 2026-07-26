from dataclasses import dataclass, field
from app.models.sector import Sector
from typing import Any, Dict, List

@dataclass
class TradeCandidate:

    symbol: str

    signal_date: str

    entry_price: float

    stop_loss: float

    risk_per_share: float

    target_2r: float

    target_3r: float

    # Metrics for future ranking
    volume_ratio: float

    distance_from_ma: float

    body_percent: float

    volume_confirmation: bool

    quality_pass: bool

    metadata: dict

    total_score: float = 0

    quantity: int = 0

    capital_required: float = 0

    market_score: float = 0

    sector_score: float = 0

    sector: Sector = Sector.UNKNOWN

    risk_amount: float = 0

    ai_confidence: float = 0.0

    ai_decision: str = "WATCH"

    ai_explanations: List[str] = field(default_factory=list)

    ai_results: Dict[str, Any] = field(default_factory=dict)