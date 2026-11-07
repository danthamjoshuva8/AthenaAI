
import logging
import math
import time


logger = logging.getLogger(__name__)


class StrategyIntelligence:
    """
    Evaluates strategy health, confidence, market regime,
    recommendations, and risk settings.
    """

    def __init__(self):
        """Initialize Strategy Intelligence Engine."""

        logger.info("Strategy Intelligence Engine initialized")

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    @staticmethod
    def _validate_number(value, field_name):
        """Validate a finite numeric input."""

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"{field_name} must be a finite numeric value"
            )

        return float(value)

    def _validate_analytics(self, analytics):
        """Validate required strategy analytics."""

        if not isinstance(analytics, dict):
            raise ValueError("Analytics must be a dictionary")

        required_fields = [
            "trade_score",
            "profit_factor",
            "win_rate",
            "expectancy"
        ]

        missing_fields = [
            field for field in required_fields
            if field not in analytics
        ]

        if missing_fields:
            raise ValueError(
                f"Missing analytics fields: {missing_fields}"
            )

        trade_score = self._validate_number(
            analytics["trade_score"],
            "Trade score"
        )

        win_rate = self._validate_number(
            analytics["win_rate"],
            "Win rate"
        )

        expectancy = self._validate_number(
            analytics["expectancy"],
            "Expectancy"
        )

        profit_factor = analytics["profit_factor"]

        if profit_factor is not None:
            profit_factor = self._validate_number(
                profit_factor,
                "Profit factor"
            )

            if profit_factor < 0:
                raise ValueError("Profit factor cannot be negative")

        if not 0 <= trade_score <= 100:
            raise ValueError("Trade score must be between 0 and 100")

        if not 0 <= win_rate <= 100:
            raise ValueError("Win rate must be between 0 and 100")

        return {
            "trade_score": trade_score,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "expectancy": expectancy
        }

    # --------------------------------------------------
    # Strategy Health
    # --------------------------------------------------

    def calculate_health_score(
        self,
        trade_score,
        profit_factor,
        win_rate,
        expectancy
    ):
        """
        Calculate strategy health score out of 100.

        Trade Score:      40 points
        Profit Factor:    30 points
        Win Rate:         20 points
        Expectancy:       10 points
        """

        start_time = time.perf_counter()

        try:
            trade_score = self._validate_number(
                trade_score, "Trade score"
            )

            win_rate = self._validate_number(
                win_rate, "Win rate"
            )

            expectancy = self._validate_number(
                expectancy, "Expectancy"
            )

            if not 0 <= trade_score <= 100:
                raise ValueError("Trade score must be between 0 and 100")

            if not 0 <= win_rate <= 100:
                raise ValueError("Win rate must be between 0 and 100")

            if profit_factor is not None:
                profit_factor = self._validate_number(
                    profit_factor, "Profit factor"
                )

                if profit_factor < 0:
                    raise ValueError("Profit factor cannot be negative")

            score = 0

            # Trade Score: Maximum 40 points
            score += min(max(trade_score, 0), 40)

            # Profit Factor: Maximum 30 points
            # Undefined profit factor receives no points.
            if profit_factor is not None:
                score += min(profit_factor * 15, 30)

            # Win Rate: Maximum 20 points
            score += min(win_rate / 2, 20)

            # Positive Expectancy: 10 points
            if expectancy > 0:
                score += 10

            result = round(min(max(score, 0), 100), 2)

            logger.info(
                "Strategy health score calculated",
                extra={
                    "health_score": result,
                    "trade_score": trade_score,
                    "profit_factor": profit_factor,
                    "win_rate": win_rate,
                    "expectancy": expectancy,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy health score calculation failed")
            raise

    def health_status(self, score):
        """Determine strategy health category."""

        score = self._validate_number(score, "Health score")

        if not 0 <= score <= 100:
            raise ValueError("Health score must be between 0 and 100")

        if score >= 90:
            return "Excellent"

        if score >= 75:
            return "Good"

        if score >= 60:
            return "Average"

        return "Poor"

    def strategy_health(self, analytics):
        """Generate strategy health assessment."""

        start_time = time.perf_counter()

        try:
            metrics = self._validate_analytics(analytics)

            score = self.calculate_health_score(
                trade_score=metrics["trade_score"],
                profit_factor=metrics["profit_factor"],
                win_rate=metrics["win_rate"],
                expectancy=metrics["expectancy"]
            )

            result = {
                "health_score": score,
                "health_status": self.health_status(score)
            }

            logger.info(
                "Strategy health assessment completed",
                extra={
                    **result,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy health assessment failed")
            raise

    # --------------------------------------------------
    # Strategy Confidence
    # --------------------------------------------------

    def calculate_confidence(self, analytics):
        """
        Calculate strategy confidence score out of 100.

        Trade Score:      40 points
        Profit Factor:    30 points
        Win Rate:         20 points
        Expectancy:       10 points
        """

        start_time = time.perf_counter()

        try:
            metrics = self._validate_analytics(analytics)

            confidence = 0

            # Trade Score: Maximum 40 points
            confidence += min(
                metrics["trade_score"] * 0.40,
                40
            )

            # Profit Factor: Maximum 30 points
            if metrics["profit_factor"] is not None:
                confidence += min(
                    metrics["profit_factor"] * 15,
                    30
                )

            # Win Rate: Maximum 20 points
            confidence += min(
                metrics["win_rate"] * 0.20,
                20
            )

            # Positive Expectancy: 10 points
            if metrics["expectancy"] > 0:
                confidence += 10

            result = round(
                min(max(confidence, 0), 100),
                2
            )

            logger.info(
                "Strategy confidence calculated",
                extra={
                    "confidence_score": result,
                    "trade_score": metrics["trade_score"],
                    "profit_factor": metrics["profit_factor"],
                    "win_rate": metrics["win_rate"],
                    "expectancy": metrics["expectancy"],
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy confidence calculation failed")
            raise

    def confidence_level(self, confidence):
        """Determine strategy confidence category."""

        confidence = self._validate_number(
            confidence, "Confidence score"
        )

        if not 0 <= confidence <= 100:
            raise ValueError(
                "Confidence score must be between 0 and 100"
            )

        if confidence >= 90:
            return "Very High"

        if confidence >= 75:
            return "High"

        if confidence >= 60:
            return "Medium"

        return "Low"

    def strategy_confidence(self, analytics):
        """Generate strategy confidence assessment."""

        start_time = time.perf_counter()

        try:
            confidence = self.calculate_confidence(analytics)

            result = {
                "confidence_score": confidence,
                "confidence_level": self.confidence_level(confidence)
            }

            logger.info(
                "Strategy confidence assessment completed",
                extra={
                    **result,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy confidence assessment failed")
            raise

    # --------------------------------------------------
    # Market Regime
    # --------------------------------------------------

    def detect_market_regime(self, latest_close, long_ma):
        """
        Identify market trend using closing price and long MA.
        """

        latest_close = self._validate_number(
            latest_close, "Latest close"
        )

        long_ma = self._validate_number(
            long_ma, "Long moving average"
        )

        if latest_close <= 0 or long_ma <= 0:
            raise ValueError(
                "Closing price and moving average must be positive"
            )

        if latest_close > long_ma:
            return "Bull"

        if latest_close < long_ma:
            return "Bear"

        return "Sideways"

    def market_regime(self, latest_close, long_ma):
        """Generate market regime assessment."""

        start_time = time.perf_counter()

        try:
            regime = self.detect_market_regime(
                latest_close,
                long_ma
            )

            result = {
                "market_regime": regime
            }

            logger.info(
                "Market regime identified",
                extra={
                    "latest_close": latest_close,
                    "long_ma": long_ma,
                    "market_regime": regime,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Market regime detection failed")
            raise

    # --------------------------------------------------
    # Strategy Recommendation
    # --------------------------------------------------

    def strategy_recommendation(
        self,
        health,
        confidence,
        market_regime
    ):
        """Generate strategy execution recommendation."""

        start_time = time.perf_counter()

        try:
            if not isinstance(health, dict):
                raise ValueError("Health must be a dictionary")

            if not isinstance(confidence, dict):
                raise ValueError("Confidence must be a dictionary")

            health_score = self._validate_number(
                health.get("health_score"),
                "Health score"
            )

            confidence_score = self._validate_number(
                confidence.get("confidence_score"),
                "Confidence score"
            )

            if not 0 <= health_score <= 100:
                raise ValueError("Invalid health score")

            if not 0 <= confidence_score <= 100:
                raise ValueError("Invalid confidence score")

            if market_regime not in ("Bull", "Bear", "Sideways", "Unknown"):
                raise ValueError("Invalid market regime")

            if (
                health_score >= 90
                and confidence_score >= 90
                and market_regime == "Bull"
            ):
                result = {
                    "recommendation": "READY",
                    "action": "BUY",
                    "reason": [
                        "Excellent Strategy Health",
                        "Very High Confidence",
                        "Bull Market"
                    ]
                }

            elif (
                health_score >= 75
                and confidence_score >= 75
            ):
                result = {
                    "recommendation": "WATCH",
                    "action": "WAIT",
                    "reason": [
                        "Good Strategy",
                        "Monitor Market"
                    ]
                }

            else:
                result = {
                    "recommendation": "AVOID",
                    "action": "NO TRADE",
                    "reason": [
                        "Weak Strategy",
                        "Low Confidence"
                    ]
                }

            logger.info(
                "Strategy recommendation generated",
                extra={
                    "health_score": health_score,
                    "confidence_score": confidence_score,
                    "market_regime": market_regime,
                    "recommendation": result["recommendation"],
                    "action": result["action"],
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy recommendation failed")
            raise

    # --------------------------------------------------
    # Risk Recommendation
    # --------------------------------------------------

    def risk_recommendation(self, health, confidence):
        """
        Generate heuristic risk settings based on strategy
        health and confidence.

        These are recommendations, not position-sizing calculations.
        """

        start_time = time.perf_counter()

        try:
            if not isinstance(health, dict):
                raise ValueError("Health must be a dictionary")

            if not isinstance(confidence, dict):
                raise ValueError("Confidence must be a dictionary")

            health_score = self._validate_number(
                health.get("health_score"),
                "Health score"
            )

            confidence_score = self._validate_number(
                confidence.get("confidence_score"),
                "Confidence score"
            )

            if not 0 <= health_score <= 100:
                raise ValueError("Invalid health score")

            if not 0 <= confidence_score <= 100:
                raise ValueError("Invalid confidence score")

            if health_score >= 90 and confidence_score >= 90:
                result = {
                    "risk_percentage": 1.0,
                    "max_positions": 10,
                    "risk_level": "Low"
                }

            elif health_score >= 75 and confidence_score >= 75:
                result = {
                    "risk_percentage": 0.75,
                    "max_positions": 7,
                    "risk_level": "Medium"
                }

            else:
                result = {
                    "risk_percentage": 0.50,
                    "max_positions": 5,
                    "risk_level": "High"
                }

            logger.info(
                "Risk recommendation generated",
                extra={
                    "health_score": health_score,
                    "confidence_score": confidence_score,
                    **result,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Risk recommendation failed")
            raise

    # --------------------------------------------------
    # Strategy Summary
    # --------------------------------------------------

    def strategy_summary(
        self,
        health,
        confidence,
        market_regime,
        recommendation,
        risk
    ):
        """Generate consolidated strategy summary."""

        start_time = time.perf_counter()

        try:
            if not all(
                isinstance(value, dict)
                for value in (
                    health,
                    confidence,
                    market_regime,
                    recommendation,
                    risk
                )
            ):
                raise ValueError(
                    "All strategy summary inputs must be dictionaries"
                )

            result = {
                "health": health,
                "confidence": confidence,
                "market_regime": market_regime,
                "recommendation": recommendation,
                "risk": risk
            }

            logger.info(
                "Strategy summary generated",
                extra={
                    "recommendation": recommendation.get(
                        "recommendation"
                    ),
                    "market_regime": market_regime.get(
                        "market_regime"
                    ),
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy summary generation failed")
            raise

    # --------------------------------------------------
    # Complete Strategy Intelligence
    # --------------------------------------------------

    def strategy_intelligence(self, summary):
        """Generate final AthenaAI strategy intelligence output."""

        start_time = time.perf_counter()

        try:
            if not isinstance(summary, dict):
                raise ValueError("Summary must be a dictionary")

            required_fields = [
                "health",
                "confidence",
                "market_regime",
                "recommendation",
                "risk"
            ]

            missing_fields = [
                field for field in required_fields
                if field not in summary
            ]

            if missing_fields:
                raise ValueError(
                    f"Strategy summary missing fields: {missing_fields}"
                )

            recommendation = summary["recommendation"]

            if not isinstance(recommendation, dict):
                raise ValueError("Invalid recommendation data")

            status = recommendation.get("recommendation")

            if status not in ("READY", "WATCH", "AVOID"):
                raise ValueError("Invalid strategy status")

            result = {
                "status": status,
                "generated_by": "AthenaAI",
                "version": "1.0",
                "summary": summary
            }

            logger.info(
                "Strategy intelligence generated successfully",
                extra={
                    "status": status,
                    "duration_seconds": round(
                        time.perf_counter() - start_time, 4
                    )
                }
            )

            return result

        except Exception:
            logger.exception("Strategy intelligence generation failed")
            raise
