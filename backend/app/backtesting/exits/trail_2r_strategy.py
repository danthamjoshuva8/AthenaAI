from app.backtesting.exits.exit_strategy import ExitStrategy


class Trail2RStrategy(ExitStrategy):

    def process(
        self,
        position,
        row
    ):

        #
        # First touch of 2R
        #

        if (

            row["signal"] == "PARTIAL_EXIT"

            and

            row["exit_reason"] == "TARGET_2R"

            and

            not position.get(
                "trail_active",
                False
            )

        ):

            position["trail_active"] = True

            position["stop_loss"] = row["exit_price"]

            return None

        #
        # 3R
        #

        if (

            row["signal"] == "PARTIAL_EXIT"

            and

            row["exit_reason"] == "TARGET_3R"

        ):

            return {

                "close_position": True,

                "sell_quantity":
                    position["remaining_quantity"],

                "exit_price":
                    row["exit_price"],

                "exit_reason":
                    "TARGET_3R"

            }

        #
        # MA Exit
        #

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