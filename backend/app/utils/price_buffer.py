from typing import List, Tuple

# (Upper Price Limit, Buffer)
BUFFER_RULES: List[Tuple[float, float]] = [
    (250, 0.25),
    (500, 0.50),
    (750, 1),
    (1200, 1.50),
    (2200, 2),
    (float("inf"), 2.50),
]


def get_buffer(price: float) -> float:
    """
    Returns the configured price buffer based on stock price.
    """

    for upper_limit, buffer in BUFFER_RULES:

        if price < upper_limit:
            return buffer

    return 6


def apply_entry_stop_buffer(
    entry_price: float,
    stop_loss: float,
    entry_enabled: bool = False,
    stop_enabled: bool = True
):

    buffer = get_buffer(entry_price)

    if entry_enabled:
        entry_price += buffer

    if stop_enabled:
        stop_loss -= buffer

    return (
        round(entry_price, 2),
        round(stop_loss, 2)
    )