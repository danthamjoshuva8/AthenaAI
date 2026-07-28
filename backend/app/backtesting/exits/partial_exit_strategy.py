from app.backtesting.exits.exit_strategy import ExitStrategy


class PartialExitStrategy(ExitStrategy):

    def process(self, position, row):

        #
        # First 50% at 2R
        #

        if (
            not position["partial_exit_2r"]
            and row["high"] >= position["target_2r"]
        ):

            position["partial_exit_2r"] = True

            return {

                "close_position": False,

                "sell_quantity": max(
                    1,
                    round(position["quantity"] * 0.5)
                ),

                "exit_price": position["target_2r"],

                "exit_reason": "TARGET_2R"

            }

        #
        # Remaining 50% at 3R
        #

        if (
            position["partial_exit_2r"]
            and not position["partial_exit_3r"]
            and row["high"] >= position["target_3r"]
        ):

            position["partial_exit_3r"] = True

            return {

                "close_position": True,

                "sell_quantity": position["remaining_quantity"],

                "exit_price": position["target_3r"],

                "exit_reason": "TARGET_3R"

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