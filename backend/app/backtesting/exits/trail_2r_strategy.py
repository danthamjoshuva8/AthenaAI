from app.backtesting.exits.exit_strategy import ExitStrategy


class Trail2RStrategy(ExitStrategy):

    def process(self, position, row):

        #
        # Partial exit at 2R
        #

        if (
            not position["partial_exit_2r"]
            and row["high"] >= position["target_2r"]
        ):

            position["partial_exit_2r"] = True
            position["stop_loss"] = position["target_2r"]

            return {
                "close_position": False,
                "sell_quantity": position["quantity"] // 2,
                "exit_price": position["target_2r"],
                "exit_reason": "TARGET_2R"
            }

        #
        # Final target
        #

        if row["high"] >= position["target_3r"]:

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": position["target_3r"],
                "exit_reason": "TARGET_3R"
            }

        #
        # Trail Stop
        #

        if (
            position["partial_exit_2r"]
            and row["low"] <= position["stop_loss"]
        ):

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": position["stop_loss"],
                "exit_reason": "TRAIL_STOP"
            }

        #
        # MA Exit
        #

        if row["signal"] == "SELL":

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": row["close"],
                "exit_reason": "SHORT_MA_BREAK"
            }

        return None