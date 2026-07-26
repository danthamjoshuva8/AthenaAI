from app.backtesting.exits.exit_strategy import ExitStrategy


class Full3RStrategy(ExitStrategy):

    def process(
        self,
        position,
        row
    ):

        #
        # Ignore every partial exit
        #

        if row["signal"] == "PARTIAL_EXIT":

            if row["exit_reason"] == "TARGET_3R":

                return {

                    "close_position": True,

                    "sell_quantity":
                        position["remaining_quantity"],

                    "exit_price":
                        row["exit_price"],

                    "exit_reason":
                        "TARGET_3R"

                }

            return None

        if row["signal"] == "SELL":

            return {

                "close_position": True,

                "sell_quantity":
                    position["remaining_quantity"],

                "exit_price":
                    row["exit_price"],

                "exit_reason":
                    row["exit_reason"]

            }

        return None