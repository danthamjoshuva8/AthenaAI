class ContextBuilder:

    async def build_context(self, trade: dict):

        return {

            # ==========================
            # Trade
            # ==========================

            "symbol": trade.get("symbol"),
            "entry_date": str(trade.get("entry_date")),
            "entry_price": trade.get("entry_price"),
            "stop_loss": trade.get("stop_loss"),
            "risk_per_share": trade.get("risk_per_share"),
            "target_2r": trade.get("target_2r"),
            "target_3r": trade.get("target_3r"),

            # ==========================
            # Strategy Scores
            # ==========================

            "strategy_score": trade.get("total_score"),
            "market_score": trade.get("market_score"),
            "sector_score": trade.get("sector_score"),

            # ==========================
            # Technical Analysis
            # ==========================

            "volume_ratio": round(trade.get("volume_ratio", 0), 2),
            "body_percent": round(trade.get("body_percent", 0), 2),
            "distance_from_ma": round(trade.get("distance_from_ma", 0), 2),

            "volume_confirmation": trade.get("volume_confirmation"),
            "quality_pass": trade.get("quality_pass"),

            # ==========================
            # Advanced Technical
            # (Safe if missing)
            # ==========================

            "atr": trade.get("atr"),
            "atr_percent": trade.get("atr_percent"),

            "distance_from_ath": trade.get("distance_from_ath"),
            "breakout_percent": trade.get("breakout_percent"),

            "ma15_slope": trade.get("ma15_slope"),
            "ma30_slope": trade.get("ma30_slope"),
            "ma150_slope": trade.get("ma150_slope"),

            "distance_from_15ma": trade.get("distance_from_15ma"),
            "distance_from_30ma": trade.get("distance_from_30ma"),
            "distance_from_150ma": trade.get("distance_from_150ma"),

            # ==========================
            # Market Context
            # ==========================

            "market_trend": trade.get("market_trend"),
            "market_score": trade.get("market_score"),

            "market_ma_distance": trade.get("market_ma_distance"),
            "market_ma_slope": trade.get("market_ma_slope"),
            "market_momentum": trade.get("market_momentum"),
            "market_atr_percent": trade.get("market_atr_percent"),

            "sector_trend": trade.get("sector_trend"),

            # ==========================
            # Company
            # ==========================

            "sector": trade.get("sector"),
            "industry": trade.get("industry"),
            "market_cap": trade.get("market_cap"),

            "historical_news": trade.get("historical_news", [])
        }