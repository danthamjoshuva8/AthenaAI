from app.backtesting.exits.exit_strategy import ExitStrategy


class Trail2RCloseStrategy(ExitStrategy):

    def process(self, position, row):

        #
        # Initialize trail flag if missing
        #

        if "trail_active" not in position:
            position["trail_active"] = False

        #
        # Activate trail after daily close above 2R
        #

        if (
            not position["trail_active"]
            and row["close"] >= position["target_2r"]
        ):

            position["trail_active"] = True
            position["stop_loss"] = position["target_2r"]

        #
        # Exit at 3R
        #

        if (
            position["trail_active"]
            and row["high"] >= position["target_3r"]
        ):

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": position["target_3r"],
                "exit_reason": "TARGET_3R"
            }

        #
        # Exit when daily close falls below 2R
        #

        if (
            position["trail_active"]
            and row["close"] < position["stop_loss"]
        ):

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": row["close"],
                "exit_reason": "TRAIL_STOP"
            }

        #
        # Exit on MA Sell
        #

        if row["signal"] == "SELL":

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": row["close"],
                "exit_reason": "SHORT_MA_BREAK"
            }

        return None