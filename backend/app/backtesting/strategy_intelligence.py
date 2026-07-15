class StrategyIntelligence:

    def __init__(

        self

    ):

        pass

    def calculate_health_score(

        self,

        trade_score,

        profit_factor,

        win_rate,

        expectancy

    ):

        score = 0

        #
        # Trade Score
        #

        score += min(

            trade_score,

            40

        )

        #
        # Profit Factor
        #

        score += min(

            profit_factor * 15,

            30

        )

        #
        # Win Rate
        #

        score += min(

            win_rate / 2,

            20

        )

        #
        # Expectancy
        #

        if expectancy > 0:

            score += 10

        return round(

            score,

            2

        )
    
    def health_status(

        self,

        score

    ):

        if score >= 90:

            return "Excellent"

        if score >= 75:

            return "Good"

        if score >= 60:

            return "Average"

        return "Poor"
    
    def strategy_health(

        self,

        analytics

    ):

        score = self.calculate_health_score(

            trade_score=analytics["trade_score"],

            profit_factor=analytics["profit_factor"],

            win_rate=analytics["win_rate"],

            expectancy=analytics["expectancy"]

        )

        return {

            "health_score": score,

            "health_status":

                self.health_status(

                    score

                )

        }
    
    def calculate_confidence(

        self,

        analytics

    ):

        confidence = 0

        #
        # Trade Score
        #

        confidence += min(

            analytics["trade_score"] * 0.40,

            40

        )

        #
        # Profit Factor
        #

        confidence += min(

            analytics["profit_factor"] * 15,

            30

        )

        #
        # Win Rate
        #

        confidence += min(

            analytics["win_rate"] * 0.20,

            20

        )

        #
        # Expectancy
        #

        if analytics["expectancy"] > 0:

            confidence += 10

        return round(

            confidence,

            2

        )
    
    def confidence_level(

        self,

        confidence

    ):

        if confidence >= 90:

            return "Very High"

        if confidence >= 75:

            return "High"

        if confidence >= 60:

            return "Medium"

        return "Low"
    
    def strategy_confidence(

        self,

        analytics

    ):

        confidence = self.calculate_confidence(

            analytics

        )

        return {

            "confidence_score": confidence,

            "confidence_level":

                self.confidence_level(

                    confidence

                )

        }
    
    def detect_market_regime(

        self,

        latest_close,

        long_ma

    ):

        if latest_close > long_ma:

            return "Bull"

        if latest_close < long_ma:

            return "Bear"

        return "Sideways"
    
    def market_regime(

        self,

        latest_close,

        long_ma

    ):

        regime = self.detect_market_regime(

            latest_close,

            long_ma

        )

        return {

            "market_regime": regime

        }
    
    def strategy_recommendation(

        self,

        health,

        confidence,

        market_regime

    ):

        if (

            health["health_score"] >= 90

            and

            confidence["confidence_score"] >= 90

            and

            market_regime == "Bull"

        ):

            return {

                "recommendation": "READY",

                "action": "BUY",

                "reason": [

                    "Excellent Strategy Health",

                    "Very High Confidence",

                    "Bull Market"

                ]

            }

        if (

            health["health_score"] >= 75

            and

            confidence["confidence_score"] >= 75

        ):

            return {

                "recommendation": "WATCH",

                "action": "WAIT",

                "reason": [

                    "Good Strategy",

                    "Monitor Market"

                ]

            }

        return {

            "recommendation": "AVOID",

            "action": "NO TRADE",

            "reason": [

                "Weak Strategy",

                "Low Confidence"

            ]

        }
    
    def risk_recommendation(

        self,

        health,

        confidence

    ):

        health_score = health["health_score"]

        confidence_score = confidence["confidence_score"]

        if health_score >= 90 and confidence_score >= 90:

            return {

                "risk_percentage": 1.0,

                "max_positions": 10,

                "risk_level": "Low"

            }

        if health_score >= 75 and confidence_score >= 75:

            return {

                "risk_percentage": 0.75,

                "max_positions": 7,

                "risk_level": "Medium"

            }

        return {

            "risk_percentage": 0.50,

            "max_positions": 5,

            "risk_level": "High"

        }
    
    def strategy_summary(

        self,

        health,

        confidence,

        market_regime,

        recommendation,

        risk

    ):

        return {

            "health": health,

            "confidence": confidence,

            "market_regime": market_regime,

            "recommendation": recommendation,

            "risk": risk

        }
    
    def strategy_intelligence(

        self,

        summary

    ):

        status = summary["recommendation"]["recommendation"]

        return {

            "status": status,

            "generated_by": "AthenaAI",

            "version": "1.0",

            "summary": summary

        }