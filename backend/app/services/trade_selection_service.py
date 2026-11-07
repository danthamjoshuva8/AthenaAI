
from requests import Session

from app.trade_selection.trade_selection_engine import TradeSelectionEngine
from app.trade_selection.trade_ranking_engine import TradeRankingEngine


class TradeSelectionService:
    """
    Provides a service layer for market scanning, trade candidate generation,
    and candidate ranking.
    """

    def __init__(self):
        """Initializes trade selection and ranking engines."""

        self.engine = TradeSelectionEngine()  # Engine responsible for market scanning and candidate generation.
        self.ranking = TradeRankingEngine()   # Engine responsible for ranking trade candidates.

    def scan_market(self, db):
        """Scans the market to identify potential trading opportunities."""
        return self.engine.scan_market(db)

    def build_candidates(
        self,
        db: Session,
        symbol: str,
        signals: list[dict]
    ):
        """Builds trade candidates for a stock using its generated signals."""
        return self.engine.build_candidates(
            db=db,
            symbol=symbol,
            signals=signals
        )

    def rank_candidates(self, candidates):
        """Ranks trade candidates based on their evaluation scores."""
        return self.ranking.rank_candidates(candidates)
