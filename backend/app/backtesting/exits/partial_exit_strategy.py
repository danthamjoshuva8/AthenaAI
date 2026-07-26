from app.backtesting.exits.exit_strategy import ExitStrategy


class PartialExitStrategy(ExitStrategy):

    def process(
        self,
        position,
        row
    ):

        if row["signal"] == "PARTIAL_EXIT":

            if not position["partial_exit_2r"]:

                return {

                    "close_position": False,

                    "sell_quantity":
                        position["remaining_quantity"] // 2,

                    "exit_price":
                        row["exit_price"],

                    "exit_reason":
                        row["exit_reason"],

                    "target": "2R"

                }

            elif not position["partial_exit_3r"]:

                return {

                    "close_position": False,

                    "sell_quantity":
                        position["remaining_quantity"] // 2,

                    "exit_price":
                        row["exit_price"],

                    "exit_reason":
                        row["exit_reason"],

                    "target": "3R"

                }

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