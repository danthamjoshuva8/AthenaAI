# Upper price limit and corresponding price buffer.
# The buffer is selected based on the stock's entry price.
BUFFER_RULES: list[tuple[float, float]] = [
    (250, 0.25),
    (500, 0.50),
    (750, 1),
    (1200, 1.50),
    (2200, 2),
    (float("inf"), 2.50),
]


def get_buffer(price: float) -> float:
    """
    Retrieve the configured price buffer based on the stock price.

    Checks the buffer rules in ascending order and returns the buffer
    associated with the first upper price limit greater than the given price.

    Args:
        price: Stock price used to determine the applicable buffer.

    Returns:
        The configured price buffer. Returns 6 if no matching rule is found.
    """

    # Find the first price range that contains the given stock price.
    for upper_limit, buffer in BUFFER_RULES:

        if price < upper_limit:
            return buffer

    # Return the fallback buffer if no configured range matches.
    return 6


def apply_entry_stop_buffer(
    entry_price: float,
    stop_loss: float,
    entry_enabled: bool = False,
    stop_enabled: bool = True
):
    """
    Apply the configured price buffer to the entry price and stop-loss.

    The entry and stop-loss adjustments can be enabled independently.
    The buffer amount is determined using the original entry price.

    Args:
        entry_price: Planned trade entry price.
        stop_loss: Initial stop-loss price.
        entry_enabled: Whether to increase the entry price by the buffer.
            Defaults to False.
        stop_enabled: Whether to decrease the stop-loss by the buffer.
            Defaults to True.

    Returns:
        A tuple containing the adjusted entry price and stop-loss,
        both rounded to two decimal places.
    """

    # Determine the applicable buffer using the original entry price.
    buffer = get_buffer(entry_price)

    # Increase the entry price when entry buffering is enabled.
    if entry_enabled:
        entry_price += buffer

    # Decrease the stop-loss when stop-loss buffering is enabled.
    if stop_enabled:
        stop_loss -= buffer

    # Return both adjusted prices rounded to two decimal places.
    return (
        round(entry_price, 2),
        round(stop_loss, 2)
    )