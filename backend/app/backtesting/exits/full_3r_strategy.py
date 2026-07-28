from app.backtesting.exits.exit_strategy import ExitStrategy


class Full3RStrategy(ExitStrategy):

    def process(self, position, row):

        if row["high"] >= position["target_3r"]:

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": position["target_3r"],
                "exit_reason": "TARGET_3R"
            }

        if row["signal"] == "SELL":

            return {
                "close_position": True,
                "sell_quantity": position["remaining_quantity"],
                "exit_price": row["close"],
                "exit_reason": "SHORT_MA_BREAK"
            }

        return None