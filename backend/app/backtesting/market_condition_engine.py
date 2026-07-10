class MarketConditionEngine:

    def classify_market(
        self,
        trade
    ):

        #
        # Temporary logic
        #
        # We'll replace this later with
        # Nifty 50 / 200 analysis
        #

        if trade["profit"] > 0:

            return "Bull"

        return "Bear"